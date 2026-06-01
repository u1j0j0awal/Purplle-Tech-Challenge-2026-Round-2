from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert item-level Purplle CSV into compact POS transactions.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, default=Path("data/pos_transactions.csv"))
    args = parser.parse_args()

    df = pd.read_csv(args.source)
    grouped = (
        df.groupby(["invoice_number", "order_date", "order_time"], dropna=True)
        .agg(basket_value_inr=("total_amount", "sum"), items=("qty", "sum"))
        .reset_index()
    )
    grouped["transaction_id"] = grouped["invoice_number"]
    grouped["timestamp"] = pd.to_datetime(
        grouped["order_date"] + " " + grouped["order_time"],
        dayfirst=True,
        utc=True,
    ).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out = grouped[["transaction_id", "timestamp", "basket_value_inr", "items"]]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"wrote {len(out)} transactions to {args.out}")


if __name__ == "__main__":
    main()
