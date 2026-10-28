from pathlib import Path
import json

import pandas as pd


def build_lifecycle(frame: pd.DataFrame, contracts_path: str | Path) -> pd.DataFrame:
    metadata = json.loads(Path(contracts_path).read_text(encoding="utf-8"))["contracts"]
    tender = {item["symbol"]: item.get("tender_start") for item in metadata}
    rows = []
    for (symbol, expiry), group in frame.groupby(["Symbol", "Expiry Date"]):
        peak_date = group.loc[group["OpenInterest"].idxmax(), "Date"] if not group.empty else None
        rows.append(
            {
                "symbol": symbol,
                "expiry_date": expiry,
                "listing_date": group["Date"].min(),
                "first_liquid_date": group.loc[group["Volume"].gt(0), "Date"].min(),
                "peak_oi_date": peak_date,
                "tender_start": pd.to_datetime(tender.get(symbol)).date() if tender.get(symbol) else None,
                "last_trade_date": group["Date"].max(),
            }
        )
    return pd.DataFrame(rows)

