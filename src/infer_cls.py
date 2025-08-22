import argparse
import json
import os

import joblib
import numpy as np
import pandas as pd

from .config import Paths
from .features import build_features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--merged_csv", default=Paths().merged_csv)
    parser.add_argument("--model_file", default=Paths().cls_model_file)
    args = parser.parse_args()

    if not os.path.exists(args.merged_csv):
        raise SystemExit(f"Merged CSV not found at {args.merged_csv}.")
    if not os.path.exists(args.model_file):
        raise SystemExit(f"Model file not found at {args.model_file}.")

    df = pd.read_csv(args.merged_csv)
    df_feat = build_features(df)

    payload = joblib.load(args.model_file)
    models = payload["models"]
    feature_cols = payload["feature_cols"]

    df_ready = df_feat.copy().dropna().reset_index(drop=True)
    if df_ready.empty:
        raise SystemExit("Not enough data for inference")

    x_row = df_ready[feature_cols].astype(float).values[-1:]

    probas = np.array([m.predict_proba(x_row)[0, 1] for m in models])
    p_mean = float(np.mean(probas))
    p_std = float(np.std(probas))
    direction = "positive" if p_mean >= 0.5 else "negative"
    confidence = p_mean if direction == "positive" else (1.0 - p_mean)

    print(json.dumps({
        "direction": direction,
        "prob_positive": p_mean,
        "prob_std": p_std,
        "conf": confidence,
        "n_models": len(models)
    }, indent=2))


if __name__ == "__main__":
    main() 