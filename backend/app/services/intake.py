import re
import uuid
from datetime import date
from pathlib import Path

import pandas as pd

from .normalize import parse_expiry_date, parse_request_date, parse_response_date, normalize_symbol

REQUIRED_COLUMNS = {"Symbol", "Date", "Expiry Date", "Open", "High", "Low", "Close", "Volume", "OpenInterest"}
DATASET_DIRECTORY = Path(__file__).resolve().parents[3] / "data" / "uploads"
SAMPLE_DATASET_PATH = Path(__file__).resolve().parents[3] / "data" / "sample" / "goldlens_synthetic.csv"
DATASET_DIRECTORY.mkdir(parents=True, exist_ok=True)


def _safe_filename(filename: str) -> str:
    stem = Path(filename).name
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._")
    return safe or "upload.csv"


def save_uploaded_dataset(file_like) -> Path:
    filename = _safe_filename(getattr(file_like, "filename", "upload.csv"))
    target = DATASET_DIRECTORY / f"{uuid.uuid4().hex}-{filename}"
    target.write_bytes(file_like.file.read())
    return target


def _describe_date_range(dates: list[date]) -> dict[str, str | None]:
    if not dates:
        return {"start": None, "end": None}
    return {"start": min(dates).strftime("%d/%m/%Y"), "end": max(dates).strftime("%d/%m/%Y")}


def validate_csv_file(path: str | Path, request_date: date | None = None) -> dict[str, object]:
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Dataset '{resolved.name}' could not be found.")
    return validate_market_file(pd.read_csv(resolved), request_date)


def validate_market_file(frame: pd.DataFrame, request_date: date | None = None) -> dict[str, object]:
    issues: list[str] = []
    warnings: list[str] = []
    if isinstance(frame, (str, Path)):
        return validate_csv_file(frame, request_date)
    if frame.empty:
        issues.append("CSV file is empty.")
        return {
            "status": "invalid",
            "row_count": 0,
            "symbol_count": 0,
            "date_range": {"start": None, "end": None},
            "symbols": [],
            "issues": issues,
            "warnings": warnings,
        }

    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        issues.append(f"Missing required columns: {', '.join(sorted(missing))}.")
        if request_date is not None:
            return {
                "status": "invalid",
                "row_count": int(len(frame)),
                "symbol_count": 0,
                "date_range": _describe_date_range([]),
                "symbols": [],
                "issues": issues,
                "warnings": warnings,
            }

    if not missing:
        normalized = frame.copy()
        normalized["Symbol"] = normalized["Symbol"].map(lambda value: normalize_symbol(str(value)) if pd.notna(value) else "")
        normalized["Date"] = pd.Series([None] * len(normalized), index=normalized.index)
        normalized["Expiry Date"] = pd.Series([None] * len(normalized), index=normalized.index)
        parsed_dates: list[date] = []
        parsed_symbols: set[str] = set()
        for idx, row in frame.iterrows():
            row_number = idx + 2
            for column in ["Symbol", "Date", "Expiry Date", "Open", "High", "Low", "Close", "Volume", "OpenInterest"]:
                if pd.isna(row[column]) or str(row[column]).strip() == "":
                    issues.append(f"Row {row_number}: missing value in '{column}'.")

            symbol_raw = row.get("Symbol")
            if pd.notna(symbol_raw) and str(symbol_raw).strip() != "":
                try:
                    symbol = normalize_symbol(str(symbol_raw))
                    parsed_symbols.add(symbol)
                    normalized.at[idx, "Symbol"] = symbol
                except (AttributeError, ValueError):
                    issues.append(f"Row {row_number}: invalid Symbol '{symbol_raw}'.")

            date_raw = row.get("Date")
            if pd.notna(date_raw) and str(date_raw).strip() != "":
                try:
                    parsed_date = parse_response_date(str(date_raw))
                    normalized.at[idx, "Date"] = parsed_date
                    parsed_dates.append(parsed_date)
                except ValueError:
                    issues.append(f"Row {row_number}: malformed market date '{date_raw}'. Expected MM/DD/YYYY.")

            expiry_raw = row.get("Expiry Date")
            if pd.notna(expiry_raw) and str(expiry_raw).strip() != "":
                try:
                    normalized.at[idx, "Expiry Date"] = parse_expiry_date(str(expiry_raw))
                except ValueError:
                    issues.append(f"Row {row_number}: malformed expiry date '{expiry_raw}'. Expected DDMMMYYYY.")

            for column in ["Open", "High", "Low", "Close", "Volume", "OpenInterest"]:
                raw_value = row.get(column)
                if pd.isna(raw_value) or str(raw_value).strip() == "":
                    continue
                try:
                    numeric_value = float(raw_value)
                except (TypeError, ValueError):
                    issues.append(f"Row {row_number}: nonnumeric value in '{column}': '{raw_value}'.")
                    continue
                if column in {"Volume", "OpenInterest"} and numeric_value < 0:
                    issues.append(f"Row {row_number}: '{column}' must be non-negative; got {numeric_value}.")
                if column in {"Open", "High", "Low", "Close"} and numeric_value <= 0:
                    issues.append(f"Row {row_number}: '{column}' must be positive; got {numeric_value}.")

            if not pd.isna(row.get("Open")) and not pd.isna(row.get("High")) and not pd.isna(row.get("Low")) and not pd.isna(row.get("Close")):
                try:
                    open_price = float(row["Open"])
                    high_price = float(row["High"])
                    low_price = float(row["Low"])
                    close_price = float(row["Close"])
                except (TypeError, ValueError):
                    pass
                else:
                    if high_price < max(open_price, close_price):
                        issues.append(f"Row {row_number}: High price {high_price} is below the intraday range maximum.")
                    if low_price > min(open_price, close_price):
                        issues.append(f"Row {row_number}: Low price {low_price} is above the intraday range minimum.")

        duplicates = frame.duplicated(subset=["Symbol", "Date", "Expiry Date", "Open", "High", "Low", "Close", "Volume", "OpenInterest"], keep=False)
        if duplicates.any():
            warnings.append(f"Duplicate rows detected: {int(duplicates.sum())} repeated records in the uploaded dataset.")

        if request_date is not None:
            if request_date.weekday() >= 5:
                issues.append(f"Request date {request_date:%d/%m/%Y} is not a trading day.")
            if parsed_dates and request_date not in parsed_dates:
                issues.append(
                    f"Requested date {request_date:%d/%m/%Y} not found; file contains "
                    f"{min(parsed_dates):%d/%m/%Y} to {max(parsed_dates):%d/%m/%Y}."
                )
            elif not parsed_dates:
                issues.append(f"Requested date {request_date:%d/%m/%Y} not found; file has no valid dates.")

        status = "invalid" if issues else "valid"
        summary = {
            "status": status,
            "row_count": int(len(frame)),
            "symbol_count": len(parsed_symbols),
            "date_range": _describe_date_range(parsed_dates),
            "symbols": sorted(parsed_symbols),
            "issues": issues,
            "warnings": warnings,
        }
        return summary

    summary = {
        "status": "invalid",
        "row_count": int(len(frame)),
        "symbol_count": 0,
        "date_range": {"start": None, "end": None},
        "symbols": [],
        "issues": issues,
        "warnings": warnings,
    }
    return summary


def read_market_file(path: str | Path, request_date: date) -> pd.DataFrame:
    frame = pd.read_csv(path)
    summary = validate_market_file(frame, request_date)
    if summary["status"] == "invalid":
        detail = "; ".join(summary["issues"]) or "CSV validation failed."
        raise ValueError(detail)
    frame = frame.copy()
    frame["Symbol"] = frame["Symbol"].map(normalize_symbol)
    frame["Date"] = frame["Date"].map(parse_response_date)
    frame["Expiry Date"] = frame["Expiry Date"].map(parse_expiry_date)
    for column in ["Open", "High", "Low", "Close", "Volume", "OpenInterest"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if request_date.weekday() >= 5:
        raise ValueError(
            f"Request date {request_date:%d/%m/%Y} is not a trading day; "
            f"file contains {frame['Date'].min():%d/%m/%Y} to {frame['Date'].max():%d/%m/%Y}"
        )
    if request_date not in set(frame["Date"]):
        raise ValueError(
            f"Requested date {request_date:%d/%m/%Y} not found; "
            f"file contains {frame['Date'].min():%d/%m/%Y} to {frame['Date'].max():%d/%m/%Y}"
        )
    return frame


def seed_demo_dataset() -> list[dict[str, object]]:
    if not SAMPLE_DATASET_PATH.exists():
        return []
    demo_target = DATASET_DIRECTORY / f"demo-{SAMPLE_DATASET_PATH.name}"
    demo_target.write_bytes(SAMPLE_DATASET_PATH.read_bytes())
    return list_dataset_records()


def list_dataset_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    if not DATASET_DIRECTORY.exists():
        return records
    demo_target = DATASET_DIRECTORY / f"demo-{SAMPLE_DATASET_PATH.name}"
    if SAMPLE_DATASET_PATH.exists() and not demo_target.exists():
        demo_target.write_bytes(SAMPLE_DATASET_PATH.read_bytes())
    files = sorted(DATASET_DIRECTORY.glob("*"), key=lambda path: ("demo-goldlens_synthetic.csv" not in path.name, path.name.lower()))
    for path in files:
        if not path.is_file():
            continue
        try:
            parsed = pd.read_csv(path)
            summary = validate_market_file(parsed)
        except Exception:
            summary = {
                "status": "invalid",
                "row_count": 0,
                "symbol_count": 0,
                "date_range": {"start": None, "end": None},
                "symbols": [],
                "issues": ["Unable to parse uploaded file."],
                "warnings": [],
            }
        records.append(
            {
                "dataset_id": path.name.split("-", 1)[0],
                "filename": path.name.split("-", 1)[1] if "-" in path.name else path.name,
                "validation": summary,
                "storage_path": str(path),
            }
        )
    if records:
        return records
    return []

