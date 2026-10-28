from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.alerts import evaluate_alert
from app.services.basis import executable_price, quote_inr_per_fine_gram, signal_inputs_as_of, PricePolicy
from app.services.intake import read_market_file
from app.services.normalize import parse_expiry_date, parse_request_date, parse_response_date, normalize_symbol
from app.services.tinyfish import TinyFishClient


client = TestClient(app)


def test_quote_fineness_golden_values():
    assert quote_inr_per_fine_gram(80000, 8, 999) == 10010.01
    assert quote_inr_per_fine_gram(80000, 8, 995) == 10050.25


def test_parser_uses_explicit_formats_and_normalizes_symbol():
    assert parse_request_date("12/03/2026") == date(2026, 3, 12)
    assert parse_response_date("03/12/2026") == date(2026, 3, 12)
    assert parse_expiry_date("04sep2026") == date(2026, 9, 4)
    assert normalize_symbol(" GOLDM ") == "GOLDM"


def test_sunday_and_wrong_date_file_are_rejected_with_both_dates(tmp_path):
    csv = tmp_path / "market.csv"
    pd.DataFrame(
        [
            {
                "Symbol": " GOLDM ",
                "Date": "03/12/2026",
                "Expiry Date": "04SEP2026",
                "Open": 1,
                "High": 1,
                "Low": 1,
                "Close": 1,
                "Volume": 1,
                "OpenInterest": 1,
            }
        ]
    ).to_csv(csv, index=False)
    with pytest.raises(ValueError, match="15/03/2026"):
        read_market_file(csv, date(2026, 3, 15))
    with pytest.raises(ValueError, match="13/03/2026"):
        read_market_file(csv, date(2026, 3, 13))


def test_alerts_are_quiet_when_costs_exceed_gap():
    result = evaluate_alert(
        symbol="GOLDM",
        pair="GOLDM/GOLDTEN",
        as_of=date(2026, 3, 12),
        gap=10,
        entry_threshold=1,
        estimated_cost=11,
        gates_passed=True,
        tender_start=None,
        last_trade_date=None,
    )
    assert result["state"] == "no_signal"
    assert result["reason_code"] == "COSTS_EXCEED_GAP"


def test_executable_price_uses_open_without_turnover_and_signal_is_prior_day_only():
    row = pd.Series({"Open": 100.0, "Volume": 10.0})
    assert executable_price(row, "buy", PricePolicy(slippage_bps=25)) == 100.25
    frame = pd.DataFrame({"Date": [date(2026, 3, 10), date(2026, 3, 11)]})
    assert list(signal_inputs_as_of(frame, pd.Timestamp("2026-03-11"))["Date"]) == [date(2026, 3, 10)]


def test_quote_api():
    response = client.post("/api/quote", json={"spot_inr": 80000, "weight_grams": 8, "fineness": 999})
    assert response.status_code == 200
    assert response.json()["inr_per_fine_gram"] == 10010.01


def test_intake_status():
    response = client.get("/api/intake/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_alert_status_evaluates_seeded_demo_dataset():
    response = client.get("/api/alerts/status")
    assert response.status_code == 200
    assert response.json() == {"state": "no_signal", "reason_code": "SHORT_HISTORY"}


def test_csv_upload_validation_accepts_valid_market_file():
    csv = b"Symbol,Date,Expiry Date,Open,High,Low,Close,Volume,OpenInterest\nGOLDM,03/10/2026,04SEP2026,80000,80100,79900,80050,100,1000\nGOLDTEN,03/10/2026,04SEP2026,80100,80200,80000,80150,100,1000\nGOLDM,03/11/2026,04SEP2026,80050,80200,80000,80100,120,1100\nGOLDTEN,03/11/2026,04SEP2026,80150,80300,80100,80250,120,1100\nGOLDM,03/12/2026,04SEP2026,80100,80300,80050,80200,130,1200\nGOLDTEN,03/12/2026,04SEP2026,80250,80400,80200,80350,130,1200\n"
    response = client.post("/api/intake/upload", files={"file": ("sample.csv", csv, "text/csv")})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "uploaded"
    assert payload["dataset"]["validation"]["status"] == "valid"
    assert payload["dataset"]["filename"] == "sample.csv"


def test_csv_upload_rejects_missing_required_columns():
    csv = b"Symbol,Date,Open,High,Low,Close\nGOLDM,03/12/2026,80000,80100,79900,80050\n"
    response = client.post("/api/intake/upload", files={"file": ("bad.csv", csv, "text/csv")})
    assert response.status_code == 400
    assert "Missing required columns" in response.json()["detail"]["message"]


def test_tinyfish_client_sends_server_side_api_key(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "completed", "id": "run-123", "result": {"ok": True}}

    def fake_post(url, *, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr("app.services.tinyfish.httpx.post", fake_post)
    result = TinyFishClient(api_key="test-key", base_url="https://example.test").run(
        url="https://example.test/data",
        goal="Return the latest gold price as JSON.",
    )
    assert result["id"] == "run-123"
    assert captured["headers"]["X-API-Key"] == "test-key"
    assert captured["json"]["goal"].startswith("Return")


def test_munimji_chat_works_and_returns_explanation():
    response = client.post(
        "/api/munimji/chat",
        json={
            "question": "Explain the cost gate and basis.",
            "language": "en",
            "context": {
                "route": "desk",
                "page": "Desk",
                "dataset_name": "goldlens_synthetic.csv",
                "pair": "GOLDM / GOLDTEN",
                "verdict": "insufficient_data",
                "reason_code": "SHORT_HISTORY",
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["language"] == "en"
    assert "basis" in payload["reply"].lower() or "cost" in payload["reply"].lower()


def test_tinyfish_endpoint_requires_server_configuration(monkeypatch):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    response = client.post(
        "/api/tinyfish/run",
        json={"url": "https://example.test", "goal": "Return JSON."},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "TINYFISH_API_KEY is not configured"
