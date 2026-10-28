from datetime import date
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from ..schemas.models import AlertResponse, AnalysisRequest, AnalysisResponse, DatasetRecord, MunimjiRequest, MunimjiResponse, QuoteRequest, QuoteResponse
from ..schemas.tinyfish import TinyFishRunRequest, TinyFishRunResponse
from ..services.alerts import evaluate_alert
from ..services.basis import quote_inr_per_fine_gram
from ..services.config import EngineConfig
from ..services.intake import DATASET_DIRECTORY, list_dataset_records, read_market_file, save_uploaded_dataset, seed_demo_dataset, validate_market_file
from ..services.lifecycle import build_lifecycle
from ..services.munimji import render_munimji_reply
from ..services.normalize import parse_request_date
from ..services.tinyfish import TinyFishClient, TinyFishConfigurationError, TinyFishRequestError

router = APIRouter()


@router.get("/health")
def api_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/intake/status")
def intake_status() -> dict[str, str]:
    return {"status": "ready"}


@router.post("/intake/upload")
def upload_market_file(file: UploadFile = File(...)) -> dict[str, object]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected.")
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
    if file.size and file.size > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum supported size is 2 MB.")

    target = save_uploaded_dataset(file)
    try:
        frame = pd.read_csv(target)
        validation = validate_market_file(frame)
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"message": f"Unable to read uploaded CSV: {exc}", "validation": {"status": "invalid", "row_count": 0, "symbol_count": 0, "date_range": {"start": None, "end": None}, "symbols": [], "issues": [str(exc)], "warnings": []}}) from exc

    if validation["status"] == "invalid":
        message = "; ".join(validation["issues"]) if validation["issues"] else "CSV validation failed."
        raise HTTPException(status_code=400, detail={"message": message, "validation": validation})

    record = {
        "dataset_id": target.name.split("-", 1)[0],
        "filename": target.name.split("-", 1)[1] if "-" in target.name else target.name,
        "validation": validation,
        "storage_path": str(target),
    }
    return {"status": "uploaded", "dataset": record}


@router.get("/datasets")
def list_datasets() -> list[DatasetRecord]:
    return [DatasetRecord(**record) for record in seed_demo_dataset() or list_dataset_records()]


@router.post("/quote", response_model=QuoteResponse)
def quote(request: QuoteRequest) -> QuoteResponse:
    return QuoteResponse(
        inr_per_fine_gram=quote_inr_per_fine_gram(
            request.spot_inr, request.weight_grams, request.fineness
        )
    )


@router.get("/alerts", response_model=list[AlertResponse])
def alerts() -> list[AlertResponse]:
    return []


@router.get("/alerts/status")
def alert_status() -> dict[str, str]:
    demo_record = next(
        (record for record in list_dataset_records() if record["dataset_id"] == "demo"),
        None,
    )
    if demo_record is None:
        return {"state": "no_signal", "reason_code": "DATASET_UNAVAILABLE"}

    validation = demo_record["validation"]
    if validation["status"] != "valid":
        return {"state": "no_signal", "reason_code": "DATASET_INVALID"}
    if validation["row_count"] < EngineConfig().minimum_observations:
        return {"state": "no_signal", "reason_code": "SHORT_HISTORY"}
    return {"state": "no_signal", "reason_code": "GATES_NOT_EVALUATED"}


@router.get("/expiry")
def expiry() -> list[dict[str, object]]:
    return []


@router.get("/basis")
def basis() -> dict[str, object]:
    return {"series": [], "signal_driver": "residual_change"}


@router.post("/analysis")
def run_analysis(request: AnalysisRequest) -> AnalysisResponse:
    dataset_path = next((Path(item["storage_path"]) for item in list_dataset_records() if item["dataset_id"] == request.dataset_id), None)
    if dataset_path is None or not dataset_path.exists():
        raise HTTPException(status_code=404, detail="Dataset not found.")
    try:
        request_date = parse_request_date(request.analysis_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid analysis date: {request.analysis_date}. Expected DD/MM/YYYY.") from exc
    try:
        frame = read_market_file(dataset_path, request_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    symbols = sorted(frame["Symbol"].unique())
    if request.pair not in {"GOLDM/GOLDTEN", "GOLDPETAL/GOLDTEN", "GOLDGUINEA/GOLDTEN", "GOLDM/GOLDGUINEA"}:
        raise HTTPException(status_code=400, detail=f"Unsupported pair '{request.pair}'.")
    config = EngineConfig()
    manifest = config.run_manifest()
    manifest["dataset_id"] = request.dataset_id
    manifest["dataset_file"] = dataset_path.name
    manifest["analysis_date"] = request.analysis_date
    manifest["pair"] = request.pair
    manifest["scenario"] = request.scenario
    manifest["source"] = "synthetic"
    manifest["slippage_bps"] = config.slippage_bps
    manifest["price_policy"] = config.executable_price_policy
    gates = []
    if len(frame) < config.minimum_observations:
        gates.append({"code": "SHORT_HISTORY", "passed": False, "detail": "Fewer than 20 observations in the dataset."})
    else:
        gates.append({"code": "OBSERVATIONS_OK", "passed": True, "detail": "Dataset has sufficient observations."})
    if request_date not in set(frame["Date"]):
        gates.append({"code": "DATE_MISSING", "passed": False, "detail": "Requested analysis date is not in the dataset."})
    else:
        gates.append({"code": "DATE_OK", "passed": True, "detail": "Requested analysis date exists in the dataset."})
    evidence = int(len(frame[frame["Date"] == request_date]))
    verdict = "insufficient_data" if any((not gate["passed"]) for gate in gates) else "ok"
    return AnalysisResponse(
        run_id=str(uuid4()),
        status="completed",
        verdict=verdict,
        reason_code=None if verdict == "ok" else "SHORT_HISTORY" if not gates[0]["passed"] else "DATE_MISSING",
        pair=request.pair,
        dataset_id=request.dataset_id,
        analysis_date=request.analysis_date,
        basis=0.0 if verdict == "ok" else None,
        cost_floor=0.0 if verdict == "ok" else None,
        net_expected=0.0 if verdict == "ok" else None,
        evidence=evidence,
        gates=[{"code": gate["code"], "passed": gate["passed"], "detail": gate["detail"]} for gate in gates],
        manifest=manifest,
    )


@router.post("/munimji/chat", response_model=MunimjiResponse)
def munimji_chat(request: MunimjiRequest) -> MunimjiResponse:
    payload = render_munimji_reply(request.question, request.language, request.context)
    return MunimjiResponse(**payload)


@router.post("/tinyfish/run", response_model=TinyFishRunResponse)
def run_tinyfish(request: TinyFishRunRequest) -> TinyFishRunResponse:
    try:
        payload = TinyFishClient().run(url=request.url, goal=request.goal)
    except TinyFishConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TinyFishRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return TinyFishRunResponse(
        status=str(payload.get("status", "unknown")),
        run_id=payload.get("id") or payload.get("run_id"),
        result=payload.get("result"),
        error=payload.get("error"),
    )
