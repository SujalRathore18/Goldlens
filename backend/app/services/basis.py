from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PricePolicy:
    name: str = "turnover_or_open"
    slippage_bps: float = 0.0


def executable_price(row: pd.Series, side: str, policy: PricePolicy) -> float:
    if "Turnover" in row.index and pd.notna(row["Turnover"]) and row["Volume"] > 0:
        price = float(row["Turnover"]) / float(row["Volume"])
    else:
        price = float(row["Open"])
    sign = 1 if side.lower() == "buy" else -1
    return price * (1 + sign * policy.slippage_bps / 10_000)


def signal_inputs_as_of(frame: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    """Return only observations known before the executable day."""
    return frame.loc[pd.to_datetime(frame["Date"]) < pd.Timestamp(day)].copy()


def quote_inr_per_fine_gram(spot_inr: float, weight_grams: float, fineness: int) -> float:
    return round(spot_inr / weight_grams / (fineness / 1000), 2)


def rolling_basis_decomposition(frame: pd.DataFrame, value_column: str = "basis") -> pd.DataFrame:
    ordered = frame.sort_values("Date").copy()
    ordered["tau"] = (ordered["Expiry Date"] - ordered["Date"]).dt.days
    ordered["f_tau"] = ordered.groupby("Expiry Date")[value_column].transform(
        lambda values: values.shift(1).expanding().mean()
    )
    ordered["roll_down"] = ordered["f_tau"] - ordered["f_tau"].shift(1)
    ordered["basis_change"] = ordered[value_column].diff()
    ordered["residual_change"] = ordered["basis_change"] - ordered["roll_down"]
    return ordered
