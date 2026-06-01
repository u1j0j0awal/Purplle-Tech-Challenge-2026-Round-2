from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class Purchase:
    transaction_id: str
    timestamp: datetime
    basket_value_inr: float


def load_pos(path: str | None = None, store_name: str = "Brigade_Bangalore") -> list[Purchase]:
    source = Path(path or os.getenv("STORE_INTEL_POS_PATH", "data/pos_transactions.csv"))
    if not source.exists():
        return []
    df = pd.read_csv(source)
    if {"transaction_id", "timestamp", "basket_value_inr"}.issubset(df.columns):
        rows = df.to_dict("records")
        return [
            Purchase(str(r["transaction_id"]), _parse_dt(r["timestamp"]), float(r["basket_value_inr"]))
            for r in rows
        ]

    # Challenge resource uses item-level Purplle POS rows. Collapse invoice lines into transactions.
    if "store_name" in df.columns:
        df = df[df["store_name"].fillna("") == store_name]
    grouped = (
        df.groupby(["invoice_number", "order_date", "order_time"], dropna=True)
        .agg(basket_value_inr=("total_amount", "sum"))
        .reset_index()
    )
    purchases: list[Purchase] = []
    for row in grouped.to_dict("records"):
        ts = pd.to_datetime(f"{row['order_date']} {row['order_time']}", dayfirst=True).to_pydatetime()
        purchases.append(
            Purchase(
                transaction_id=str(row["invoice_number"]),
                timestamp=ts.replace(tzinfo=timezone.utc),
                basket_value_inr=float(row["basket_value_inr"]),
            )
        )
    return sorted(purchases, key=lambda p: p.timestamp)


def _parse_dt(value: object) -> datetime:
    ts = pd.to_datetime(value, utc=True).to_pydatetime()
    return ts.astimezone(timezone.utc)
