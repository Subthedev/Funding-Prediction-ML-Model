from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from flask import Flask, jsonify, render_template, redirect, url_for

from src.config import Paths, DEFAULT_COIN, DEFAULT_INTERVAL
from src.utils import ensure_dir, now_ms, days_ago_ms, floor_hour_ms
from src.hyperliquid_api import (
    get_current_funding_for_coin,
    get_predicted_funding_for_coin,
    fetch_funding_history,
)
from src.fetch_data import funding_df
from src.features import build_features
import pandas as pd
import joblib


app = Flask(__name__, template_folder="templates")
paths = Paths()
ensure_dir(paths.data_dir)
ensure_dir(paths.models_dir)


def _load_cls_model():
    payload = joblib.load(paths.cls_model_file)
    return payload["models"], payload["feature_cols"]


def _load_reg_model():
    payload = joblib.load(paths.model_file)
    return payload["models"], payload["feature_cols"]


def _latest_dataset(days: int = 14) -> pd.DataFrame:
    # Minimal: use funding history only (no heavy candles) for quick endpoints
    end = now_ms()
    start = days_ago_ms(days)
    fundings = fetch_funding_history(DEFAULT_COIN, start, end)
    fdf = funding_df(fundings)
    # Create a stub candles alignment to keep features working if needed
    return fdf


def _predict_direction() -> Dict[str, Any]:
    models, feature_cols = _load_cls_model()
    df = _latest_dataset(14)
    if df.empty:
        return {"error": "no data"}
    # Build features requires merged df; for safety, only use funding features
    df_feat = build_features(pd.DataFrame({
        "hour": df["time"],
        "fundingRate": df.get("fundingRate", 0),
        "premium": df.get("premium", 0),
        "c": pd.Series(dtype=float),
        "v": pd.Series(dtype=float),
    })).dropna().reset_index(drop=True)
    if df_feat.empty:
        return {"error": "not enough features"}
    x = df_feat[feature_cols].astype(float).values[-1:]
    import numpy as np
    probas = np.array([m.predict_proba(x)[0, 1] for m in models])
    p = float(probas.mean())
    direction = "positive" if p >= 0.5 else "negative"
    conf = p if direction == "positive" else (1.0 - p)
    return {"direction": direction, "prob_positive": p, "confidence": conf, "n_models": len(models)}


def _predict_numeric() -> Dict[str, Any]:
    models, feature_cols = _load_reg_model()
    df = _latest_dataset(14)
    if df.empty:
        return {"error": "no data"}
    df_feat = build_features(pd.DataFrame({
        "hour": df["time"],
        "fundingRate": df.get("fundingRate", 0),
        "premium": df.get("premium", 0),
        "c": pd.Series(dtype=float),
        "v": pd.Series(dtype=float),
    })).dropna().reset_index(drop=True)
    if df_feat.empty:
        return {"error": "not enough features"}
    x = df_feat[feature_cols].astype(float).values[-1:]
    import numpy as np
    preds = np.array([m.predict(x)[0] for m in models])
    return {"pred_next_funding": float(preds.mean()), "pred_std": float(preds.std()), "n_models": len(models)}


@app.route("/")
def root():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/summary")
def api_summary():
    hl_current = get_current_funding_for_coin(DEFAULT_COIN) or {}
    hl_pred = get_predicted_funding_for_coin(DEFAULT_COIN) or {}
    cls = _predict_direction()
    reg = _predict_numeric()

    # robust next funding time
    now = now_ms()
    raw_next = None
    if isinstance(hl_pred, dict):
        raw_next = hl_pred.get("nextFundingTime")
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