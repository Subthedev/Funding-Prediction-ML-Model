import pandas as pd
import numpy as np
from typing import List, Optional, cast


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["ts"] = pd.to_datetime(out["hour"], unit="ms", utc=True)
    out["hour_of_day"] = out["ts"].dt.hour
    out["day_of_week"] = out["ts"].dt.dayofweek
    return out


def add_cyclical_time_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    two_pi = 2 * np.pi
    out["hour_sin"] = np.sin(two_pi * out["hour_of_day"].astype(float) / 24.0)
    out["hour_cos"] = np.cos(two_pi * out["hour_of_day"].astype(float) / 24.0)
    out["dow_sin"] = np.sin(two_pi * out["day_of_week"].astype(float) / 7.0)
    out["dow_cos"] = np.cos(two_pi * out["day_of_week"].astype(float) / 7.0)
    return out


def add_price_features(df: pd.DataFrame, price_col: str = "c") -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    price = cast(pd.Series, out[price_col]).astype(float)
    out["ret_1"] = price.pct_change(1)
    out["ret_3"] = price.pct_change(3)
    out["ret_6"] = price.pct_change(6)
    out["ret_12"] = price.pct_change(12)
    out["vol_6"] = price.pct_change().rolling(6).std()
    out["vol_12"] = price.pct_change().rolling(12).std()
    out["vol_24"] = price.pct_change().rolling(24).std()
    out["rsi_14"] = compute_rsi(price, 14)
    out["z_score_24"] = zscore(price, 24)
    return out


def add_lags(df: pd.DataFrame, cols: List[str], lags: Optional[List[int]] = None, ema_spans: Optional[List[int]] = None) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    lag_list = lags if lags is not None else [1, 2, 3, 6, 12, 24]
    ema_list = ema_spans if ema_spans is not None else [12, 24]
    for col in cols:
        if col not in out.columns:
            continue
        series = cast(pd.Series, out[col]).astype(float)
        for k in lag_list:
            out[f"{col}_lag_{k}"] = series.shift(k)
        for s in ema_list:
            out[f"{col}_ema_{s}"] = series.ewm(span=s, adjust=False).mean()
        out[f"{col}_abs"] = series.abs()
    return out


def add_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "v" not in df.columns:
        return df
    out = df.copy()
    vol = cast(pd.Series, out["v"]).astype(float)
    out["vol_chg_1"] = vol.pct_change(1)
    out["vol_chg_6"] = vol.pct_change(6)
    out["vol_ma_6"] = vol.rolling(6).mean()
    out["vol_ma_24"] = vol.rolling(24).mean()
    return out


def compute_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = (delta.clip(lower=0)).ewm(alpha=1 / float(period), adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / float(period), adjust=False).mean()
    rs = gain / (loss + 1e-12)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return cast(pd.Series, rsi)


def zscore(series: pd.Series, window: int) -> pd.Series:
    mean_series = cast(pd.Series, series.rolling(window).mean())
    std_series = cast(pd.Series, series.rolling(window).std())
    denom = std_series + 1e-12
    z = (series - mean_series) / denom
    return cast(pd.Series, z)


def build_features(merged: pd.DataFrame) -> pd.DataFrame:
    df = merged.copy()
    # Use merged fields: hour, fundingRate, premium, o,h,l,c,v etc.
    df = add_time_features(df)
    df = add_cyclical_time_features(df)
    df = add_price_features(df, price_col="c")
    df = add_lags(df, cols=["fundingRate", "premium"])  # generalized lags and EMAs
    df = add_volume_features(df)
    return df 