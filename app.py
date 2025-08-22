from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from flask import Flask, jsonify, render_template, redirect, url_for

from src.config import Paths, DEFAULT_COIN
from src.utils import ensure_dir, now_ms, days_ago_ms, floor_hour_ms
from src.hyperliquid_api import (
    get_current_funding_for_coin,
    get_predicted_funding_for_coin,
    fetch_funding_history,
)
from src.fetch_data import funding_df
import pandas as pd

try:
    import joblib  # type: ignore
except Exception:  # pragma: no cover
    joblib = None  # type: ignore

try:
    from src.features import build_features  # type: ignore
except Exception:
    build_features = None  # type: ignore


app = Flask(__name__, template_folder="templates")
paths = Paths()
ensure_dir(paths.data_dir)
ensure_dir(paths.models_dir)


def _safe_load(payload_path: str) -> Tuple[list[Any], list[str]]:
    if joblib is None:
        return [], []
    if not os.path.exists(payload_path):
        return [], []
    try:
        payload = joblib.load(payload_path)
        models = payload.get("models", [])
        feature_cols = payload.get("feature_cols", [])
        return models, feature_cols
    except Exception:
        return [], []


def _load_cls_model() -> Tuple[list[Any], list[str]]:
    return _safe_load(paths.cls_model_file)


def _load_reg_model() -> Tuple[list[Any], list[str]]:
    return _safe_load(paths.model_file)


def _latest_dataset(days: int = 14) -> pd.DataFrame:
    end = now_ms()
    start = days_ago_ms(days)
    try:
        fundings = fetch_funding_history(DEFAULT_COIN, start, end)
        fdf = funding_df(fundings)
        return fdf
    except Exception:
        return pd.DataFrame()


def _features_from_funding(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    if build_features is None:
        # Minimal fallback features: use simple rolling stats on funding
        out = pd.DataFrame({
            "hour": df["time"],
            "fundingRate": df.get("fundingRate", 0),
            "premium": df.get("premium", 0),
        }).dropna()
        for w in (3, 6, 12, 24):
            out[f"fundingRate_ema_{w}"] = out["fundingRate"].ewm(span=w, adjust=False).mean()
        out = out.dropna()
        return out.reset_index(drop=True)
    try:
        return build_features(pd.DataFrame({
            "hour": df["time"],
            "fundingRate": df.get("fundingRate", 0),
            "premium": df.get("premium", 0),
            "c": pd.Series(dtype=float),
            "v": pd.Series(dtype=float),
        })).dropna().reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def _predict_direction() -> Dict[str, Any]:
    models, feature_cols = _load_cls_model()
    df = _latest_dataset(14)
    feat = _features_from_funding(df)
    if feat.empty or not feature_cols or not models:
        # Conservative neutral fallback
        return {"direction": "wait", "prob_positive": 0.5, "confidence": 0.5, "n_models": len(models)}
    x = feat[feature_cols].astype(float).values[-1:]
    import numpy as np
    try:
        probas = np.array([m.predict_proba(x)[0, 1] for m in models])
        p = float(probas.mean())
        direction = "positive" if p >= 0.5 else "negative"
        conf = p if direction == "positive" else (1.0 - p)
        return {"direction": direction, "prob_positive": p, "confidence": conf, "n_models": len(models)}
    except Exception:
        return {"direction": "wait", "prob_positive": 0.5, "confidence": 0.5, "n_models": len(models)}


def _predict_numeric() -> Dict[str, Any]:
    models, feature_cols = _load_reg_model()
    df = _latest_dataset(14)
    feat = _features_from_funding(df)
    if feat.empty or not feature_cols or not models:
        return {"pred_next_funding": 0.0, "pred_std": 0.0, "n_models": len(models)}
    x = feat[feature_cols].astype(float).values[-1:]
    import numpy as np
    try:
        preds = np.array([m.predict(x)[0] for m in models])
        return {"pred_next_funding": float(preds.mean()), "pred_std": float(preds.std()), "n_models": len(models)}
    except Exception:
        return {"pred_next_funding": 0.0, "pred_std": 0.0, "n_models": len(models)}


@app.route("/")
def root():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/summary")
def api_summary():
    try:
        hl_current = get_current_funding_for_coin(DEFAULT_COIN) or {}
    except Exception:
        hl_current = {}
    try:
        hl_pred = get_predicted_funding_for_coin(DEFAULT_COIN) or {}
    except Exception:
        hl_pred = {}
    cls = _predict_direction()
    reg = _predict_numeric()

    now = now_ms()
    raw_next = hl_pred.get("nextFundingTime") if isinstance(hl_pred, dict) else None
    next_ms = raw_next if isinstance(raw_next, (int, float)) else None
    if next_ms is None:
        next_ms = floor_hour_ms(now) + 60 * 60 * 1000
    else:
        if next_ms < now - 5 * 60 * 1000:
            hours_behind = int((now - next_ms) // (60 * 60 * 1000)) + 1
            next_ms = next_ms + hours_behind * 60 * 60 * 1000
        if next_ms > now + 3 * 60 * 60 * 1000:
            next_ms = floor_hour_ms(now) + 60 * 60 * 1000

    return jsonify({
        "predictedFundingRate": reg,
        "predictedDirection": cls,
        "liveFunding": hl_current,
        "nextFundingTime": int(next_ms),
        "coin": DEFAULT_COIN,
        "serverTime": int(now),
        "fundingIntervalSeconds": 3600,
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7860"))
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True) 