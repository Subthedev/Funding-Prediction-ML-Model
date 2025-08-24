from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Dict, Any

from flask import Flask, render_template, jsonify, redirect, url_for
import pandas as pd
import joblib
try:
    import gradio as gr  # type: ignore
except Exception:
    gr = None  # type: ignore

from src.config import Paths, DEFAULT_COIN, DEFAULT_INTERVAL
from src.hyperliquid_api import get_current_funding_for_coin, get_predicted_funding_for_coin
from src.features import build_features
from src.fetch_data import merge_on_hour, funding_df, candles_df
from src.utils import ensure_dir, now_ms, days_ago_ms, floor_hour_ms
from src.hyperliquid_api import fetch_funding_history, fetch_candles


app = Flask(__name__)
paths = Paths()
ensure_dir(paths.data_dir)
ensure_dir(paths.models_dir)


def load_cls_model():
    payload = joblib.load(paths.cls_model_file)
    return payload["models"], payload["feature_cols"]


def load_reg_model():
    payload = joblib.load(paths.model_file)
    return payload["models"], payload["feature_cols"]


def latest_dataset(days: int = 7) -> pd.DataFrame:
    end = now_ms()
    start = days_ago_ms(days)
    fundings = fetch_funding_history(DEFAULT_COIN, start, end)
    candles = fetch_candles(DEFAULT_COIN, DEFAULT_INTERVAL, start, end)
    fdf = funding_df(fundings)
    cdf = candles_df(candles)
    merged = merge_on_hour(fdf, cdf)
    return merged


def predict_direction() -> Dict[str, Any]:
    models, feature_cols = load_cls_model()
    df = latest_dataset(14)
    df_feat = build_features(df).dropna().reset_index(drop=True)
    if df_feat.empty:
        return {"error": "Not enough data to predict"}
    x_row = df_feat[feature_cols].astype(float).values[-1:]
    import numpy as np
    probas = np.array([m.predict_proba(x_row)[0, 1] for m in models])
    p_mean = float(probas.mean())
    direction = "positive" if p_mean >= 0.5 else "negative"
    conf = p_mean if direction == "positive" else (1.0 - p_mean)
    return {
        "direction": direction,
        "prob_positive": p_mean,
        "confidence": conf,
        "n_models": len(models),
    }


def predict_numeric() -> Dict[str, Any]:
    models, feature_cols = load_reg_model()
    df = latest_dataset(14)
    df_feat = build_features(df).dropna().reset_index(drop=True)
    if df_feat.empty:
        return {"error": "Not enough data"}
    x_row = df_feat[feature_cols].astype(float).values[-1:]
    import numpy as np
    preds = np.array([m.predict(x_row)[0] for m in models])
    return {"pred_next_funding": float(preds.mean()), "pred_std": float(preds.std()), "n_models": len(models)}


def append_prediction_to_log(direction: str, prob_positive: float) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    row = {
        "time": ts,
        "direction": direction,
        "prob_positive": prob_positive,
    }
    if os.path.exists(paths.predictions_log):
        df = pd.read_csv(paths.predictions_log)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])
    df.to_csv(paths.predictions_log, index=False)


def realized_direction_after(ts_iso: str) -> str | None:
    try:
        ts = datetime.fromisoformat(ts_iso)
    except Exception:
        return None
    start = int(ts.timestamp() * 1000)
    end = now_ms()
    fundings = fetch_funding_history(DEFAULT_COIN, start, end)
    fdf = funding_df(fundings)
    if fdf.empty:
        return None
    next_events = fdf[fdf["time"] > start]
    if next_events.empty:
        return None
    rate = float(next_events.iloc[0]["fundingRate"])
    return "positive" if rate > 0 else "negative"


def compute_actual_direction() -> Dict[str, Any]:
    if not os.path.exists(paths.predictions_log):
        return {"message": "No predictions yet"}
    logs = pd.read_csv(paths.predictions_log)
    if logs.empty:
        return {"message": "No predictions yet"}
    latest = logs.iloc[-1]
    realized = realized_direction_after(str(latest["time"]))
    if realized is None:
        return {"message": "Awaiting realized funding"}
    correct = str(realized == latest["direction"]).lower()
    return {
        "last_prediction_time": latest["time"],
        "predicted_direction": latest["direction"],
        "prob_positive": float(latest.get("prob_positive", 0.0)),
        "realized_direction": realized,
        "correct": correct,
    }


def compute_accuracy(max_days: int = 14) -> Dict[str, Any]:
    if not os.path.exists(paths.predictions_log):
        return {"count": 0, "correct": 0, "accuracy": None}
    logs = pd.read_csv(paths.predictions_log)
    if logs.empty:
        return {"count": 0, "correct": 0, "accuracy": None}
    cutoff_ms = days_ago_ms(max_days)
    logs["time_ms"] = pd.to_datetime(logs["time"]).astype("int64") // 10**6
    logs = logs[logs["time_ms"] >= cutoff_ms].reset_index(drop=True)
    if logs.empty:
        return {"count": 0, "correct": 0, "accuracy": None}
    correct = 0
    total = 0
    for _, row in logs.iterrows():
        realized = realized_direction_after(str(row["time"]))
        if realized is None:
            continue
        total += 1
        if realized == str(row["direction"]):
            correct += 1
    acc = (correct / total) if total > 0 else None
    return {"count": total, "correct": correct, "accuracy": acc}


@app.route("/")
def index():
    # Always serve the React dashboard
    return redirect(url_for('dashboard'))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/status")
def api_status():
    hl_current = get_current_funding_for_coin(DEFAULT_COIN) or {}
    hl_pred = get_predicted_funding_for_coin(DEFAULT_COIN) or {}
    pred = predict_direction()
    return jsonify({
        "hl_current": hl_current,
        "hl_pred": hl_pred,
        "prediction": pred,
    })


@app.route("/api/summary")
def api_summary():
    hl_current = get_current_funding_for_coin(DEFAULT_COIN) or {}
    hl_pred = get_predicted_funding_for_coin(DEFAULT_COIN) or {}
    cls = predict_direction()
    reg = predict_numeric()
    cmp_res = compute_actual_direction()
    acc = compute_accuracy()

    # Robust next funding time (ms)
    now = now_ms()
    raw_next = None
    if isinstance(hl_pred, dict):
        raw_next = hl_pred.get("nextFundingTime")
    effective_next = raw_next if isinstance(raw_next, (int, float)) else None
    if effective_next is None:
        effective_next = floor_hour_ms(now) + 60 * 60 * 1000
    else:
        # If stale (in the past), roll forward to the next hour boundary
        if effective_next < now - 5 * 60 * 1000:
            hours_behind = int((now - effective_next) // (60 * 60 * 1000)) + 1
            effective_next = effective_next + hours_behind * 60 * 60 * 1000
        # If way in the future (rare), clamp to next hour
        if effective_next > now + 3 * 60 * 60 * 1000:
            effective_next = floor_hour_ms(now) + 60 * 60 * 1000

    return jsonify({
        "predictedFundingRate": reg,
        "predictedDirection": cls,
        "liveFunding": hl_current,
        "nextFundingTime": int(effective_next),
        "lastComparison": cmp_res,
        "accuracy": acc,
        "coin": DEFAULT_COIN,
        "serverTime": int(now),
        "fundingIntervalSeconds": 3600,
    })


@app.route("/api/history")
def api_history():
    # Return recent funding history and predictions log for charting
    end = now_ms()
    start = days_ago_ms(3)
    fundings = fetch_funding_history(DEFAULT_COIN, start, end)
    fdf = funding_df(fundings)
    hist = [
        {"time": int(row["time"]), "fundingRate": float(row["fundingRate"]) if pd.notna(row["fundingRate"]) else None}
        for _, row in fdf.tail(500).iterrows()
    ]
    preds = []
    if os.path.exists(paths.predictions_log):
        logs = pd.read_csv(paths.predictions_log)
        for _, row in logs.tail(200).iterrows():
            realized = realized_direction_after(str(row["time"]))
            preds.append({
                "time": str(row["time"]),
                "direction": str(row["direction"]),
                "prob_positive": float(row.get("prob_positive", 0.0)),
                "realized": realized,
                "correct": realized == str(row["direction"]),
            })
    return jsonify({"fundingHistory": hist, "predictionsLog": preds})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


def _find_free_port(preferred: int = 8000, max_tries: int = 20) -> int:
    import socket
    port = preferred
    for _ in range(max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1
    return preferred


def greet(name):
    return f"Hello {name}, welcome to IgniteX 🚀!"

if gr is not None:
    demo = gr.Interface(fn=greet, inputs="text", outputs="text")
else:
    demo = None  # type: ignore

# Remove the following block for deployment:
# if __name__ == "__main__":
#     host = os.getenv("HOST", "127.0.0.1")
#     try:
#         base_port = int(os.getenv("PORT", "8000"))
#     except ValueError:
#         base_port = 8000
#     port = _find_free_port(base_port)
#     print(f"Starting server on http://{host}:{port}")
#     app.run(host=host, port=port, debug=True, use_reloader=False, threaded=True)

# For local development, you can keep this:
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
    # Launch Gradio app if available
    if demo is not None:
        demo.launch()