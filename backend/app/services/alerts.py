from datetime import date

import pandas as pd


def evaluate_alert(
    *,
    symbol: str,
    pair: str,
    as_of: date,
    gap: float,
    entry_threshold: float,
    estimated_cost: float,
    gates_passed: bool,
    tender_start: date | None,
    last_trade_date: date | None,
) -> dict[str, object]:
    if not gates_passed:
        reason = "GATE_FAILED"
    elif gap <= entry_threshold:
        reason = "BELOW_ENTRY_THRESHOLD"
    elif tender_start and as_of >= tender_start and (last_trade_date is None or as_of <= last_trade_date):
        reason = "TENDER_PERIOD"
    elif gap <= estimated_cost:
        reason = "COSTS_EXCEED_GAP"
    else:
        return {"state": "alert", "reason_code": "ENTRY_READY", "symbol": symbol, "date": as_of, "pair": pair}
    return {"state": "no_signal", "reason_code": reason, "symbol": symbol, "date": as_of, "pair": pair}


def quiet_alerts(rows: pd.DataFrame, **kwargs: object) -> list[dict[str, object]]:
    alerts: dict[tuple[str, date], dict[str, object]] = {}
    for row in rows.itertuples(index=False):
        result = evaluate_alert(symbol=row.Symbol, as_of=row.Date, **kwargs)
        alerts.setdefault((str(row.Symbol), row.Date), result)
    return [result for result in alerts.values() if result["state"] == "alert"]

