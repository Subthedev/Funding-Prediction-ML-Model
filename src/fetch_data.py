import argparse
import json
import os
from typing import List

import pandas as pd

from .config import DEFAULT_COIN, DEFAULT_INTERVAL, DEFAULT_HISTORY_DAYS, Paths
from .hyperliquid_api import fetch_funding_history, fetch_candles, coin_in_universe
from .utils import ensure_dir, days_ago_ms, now_ms, floor_hour_ms


def funding_df(records: List[dict]) -> pd.DataFrame:
    if not records:
        df_empty: pd.DataFrame = pd.DataFrame({
            "time": pd.Series(dtype="int64"),
            "fundingRate": pd.Series(dtype="float64"),
            "premium": pd.Series(dtype="float64"),
            "coin": pd.Series(dtype="string"),
        })
        return df_empty
    df = pd.DataFrame(records)
    for col in ["fundingRate", "premium"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values("time").reset_index(drop=True)
    return df


def candles_df(records: List[dict]) -> pd.DataFrame:
    if not records:
        df_empty: pd.DataFrame = pd.DataFrame({
            "t": pd.Series(dtype="int64"),
            "T": pd.Series(dtype="int64"),
            "o": pd.Series(dtype="float64"),
            "h": pd.Series(dtype="float64"),
            "l": pd.Series(dtype="float64"),
            "c": pd.Series(dtype="float64"),
            "v": pd.Series(dtype="float64"),
            "i": pd.Series(dtype="string"),
            "s": pd.Series(dtype="string"),
            "n": pd.Series(dtype="int64"),
        })
        return df_empty
    df = pd.DataFrame(records)
    # Cast numeric cols
    for col in ["t", "T", "n"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce", downcast="integer")
    for col in ["o", "h", "l", "c", "v"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values("t").reset_index(drop=True)
    return df


def merge_on_hour(funding: pd.DataFrame, candles: pd.DataFrame) -> pd.DataFrame:
    # Align funding events to the most recent candle at or before the funding hour.
    if funding.empty or candles.empty:
        return pd.DataFrame()
    funding = funding.copy()
    funding["hour"] = funding["time"].apply(floor_hour_ms)
    candles = candles.copy()
    candles["hour"] = candles["t"]
    merged = pd.merge_asof(
        funding.sort_values("hour"),
        candles.sort_values("hour"),
        on="hour",
        direction="backward",
        tolerance=60 * 60 * 1000,  # within 1h
    )
    return merged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--coin", default=DEFAULT_COIN)
    parser.add_argument("--interval", default=DEFAULT_INTERVAL)
    parser.add_argument("--days", type=int, default=DEFAULT_HISTORY_DAYS)
    args = parser.parse_args()

    paths = Paths()
    ensure_dir(paths.data_dir)

    if not coin_in_universe(args.coin):
        raise SystemExit(f"Coin {args.coin} not found in Hyperliquid universe")

    end = now_ms()
    start = days_ago_ms(int(args.days))

    fundings = fetch_funding_history(str(args.coin), start, end)
    fdf = funding_df(fundings)
    fdf.to_csv(paths.funding_csv, index=False)

    candles = fetch_candles(str(args.coin), str(args.interval), start, end)
    cdf = candles_df(candles)
    cdf.to_csv(paths.candles_csv, index=False)

    merged = merge_on_hour(fdf, cdf)
    if not merged.empty:
        merged.to_csv(paths.merged_csv, index=False)

    print(json.dumps({
        "funding_rows": int(fdf.shape[0]),
        "candles_rows": int(cdf.shape[0]),
        "merged_rows": int(merged.shape[0] if not merged.empty else 0),
        "funding_csv": paths.funding_csv,
        "candles_csv": paths.candles_csv,
        "merged_csv": paths.merged_csv,
    }, indent=2))


if __name__ == "__main__":
    main() 