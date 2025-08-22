import argparse
import json
import os
from typing import List, Tuple, Protocol, runtime_checkable, cast

import joblib
import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

from .config import Paths
from .features import build_features


TARGET_COL = "fundingRate"


@runtime_checkable
class RegressorProtocol(Protocol):
    def predict(self, X: NDArray[np.float64]) -> NDArray[np.float64]:
        ...


def prepare_dataset(df: pd.DataFrame) -> Tuple[NDArray[np.float64], NDArray[np.float64], List[str], pd.DataFrame]:
    df = df.copy()
    # Target is next period funding rate
    df["target_next_funding"] = df[TARGET_COL].shift(-1)

    # Drop rows with NaNs introduced by shifting and feature windows
    df = df.dropna().reset_index(drop=True)

    # Feature columns
    drop_cols = {
        "ts", "i", "s", "n", "o", "h", "l", "hour", TARGET_COL, "time", "target_next_funding"
    }
    feature_cols = [c for c in df.columns if c not in drop_cols and df[c].dtype != "O"]

    X_arr = cast(NDArray[np.float64], np.asarray(df[feature_cols].astype(float).values, dtype=np.float64))
    y_arr = cast(NDArray[np.float64], np.asarray(df["target_next_funding"].astype(float).values, dtype=np.float64))
    return X_arr, y_arr, feature_cols, df


def train_model(X: NDArray[np.float64], y: NDArray[np.float64], n_splits: int = 5) -> Tuple[List[HistGradientBoostingRegressor], dict[str, float]]:
    tscv = TimeSeriesSplit(n_splits=n_splits)
    oof_preds: NDArray[np.float64] = np.zeros_like(y)
    models: List[HistGradientBoostingRegressor] = []

    for _fold, (trn_idx, val_idx) in enumerate(tscv.split(X), start=1):
        X_trn, y_trn = X[trn_idx], y[trn_idx]
        X_val: NDArray[np.float64] = X[val_idx]

        model = HistGradientBoostingRegressor(
            max_depth=None,
            max_iter=500,
            learning_rate=0.05,
            l2_regularization=1e-2,
            random_state=42,
        )
        model.fit(X_trn, y_trn)
        preds: NDArray[np.float64] = model.predict(X_val)
        oof_preds[val_idx] = preds
        models.append(model)

    mae = float(mean_absolute_error(y, oof_preds))
    r2 = float(r2_score(y, oof_preds))
    return models, {"mae": mae, "r2": r2}


def main():
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--merged_csv", default=Paths().merged_csv)
    _ = parser.add_argument("--model_out", default=Paths().model_file)
    _ = parser.add_argument("--meta_out", default=Paths().model_meta)
    args = parser.parse_args()

    merged_csv: str = str(args.merged_csv)
    model_out: str = str(args.model_out)
    meta_out: str = str(args.meta_out)

    if not os.path.exists(merged_csv):
        raise SystemExit(f"Merged CSV not found at {merged_csv}. Run fetch_data.py first.")

    df: pd.DataFrame = pd.read_csv(merged_csv)
    df_feat = build_features(df)
    X, y, feature_cols, df_ready = prepare_dataset(df_feat)

    models, metrics = train_model(X, y)

    # Save the last model as production model and meta
    os.makedirs(os.path.dirname(model_out), exist_ok=True)
    _ = joblib.dump({"models": models, "feature_cols": feature_cols}, model_out)

    with open(meta_out, "w") as f:
        json.dump({"metrics": metrics, "num_rows": int(df_ready.shape[0])}, f, indent=2)

    print(json.dumps({"metrics": metrics, "model": model_out, "meta": meta_out}, indent=2))


if __name__ == "__main__":
    main() 