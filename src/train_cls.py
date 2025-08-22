import argparse
import json
import os
from typing import List, Tuple, Protocol, runtime_checkable, cast

import joblib
import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.calibration import CalibratedClassifierCV
from collections import Counter
from datetime import datetime, timezone

from .config import Paths
from .features import build_features


TARGET_COL = "fundingRate"


@runtime_checkable
class ClassifierProtocol(Protocol):
    def predict_proba(self, X: NDArray[np.float64]) -> NDArray[np.float64]:
        ...


def prepare_dataset(df: pd.DataFrame) -> Tuple[NDArray[np.float64], NDArray[np.int_], List[str], pd.DataFrame]:
    df = df.copy()
    # Define classification target: sign of next funding (1 if > 0 else 0)
    df["target_next_funding"] = df[TARGET_COL].shift(-1)
    df = df.dropna().reset_index(drop=True)
    df["label"] = (df["target_next_funding"] > 0).astype(int)

    drop_cols = {
        "ts", "i", "s", "n", "o", "h", "l", "hour", TARGET_COL, "time", "target_next_funding", "label"
    }
    feature_cols = [c for c in df.columns if c not in drop_cols and df[c].dtype != "O"]
    X_arr = cast(NDArray[np.float64], np.asarray(df[feature_cols].astype(float).values, dtype=np.float64))
    y_arr = cast(NDArray[np.int_], np.asarray(df["label"].astype(int).values, dtype=np.int_))
    return X_arr, y_arr, feature_cols, df


def compute_sample_weights(y: NDArray[np.int_]) -> NDArray[np.float64]:
    counts = Counter(int(v) for v in y)
    total = int(len(y))
    weights = np.array([total / (2 * counts[int(val)]) for val in y], dtype=np.float64)
    return weights


def train_model(X: NDArray[np.float64], y: NDArray[np.int_], n_splits: int = 5) -> Tuple[List[CalibratedClassifierCV], dict[str, float]]:
    tscv = TimeSeriesSplit(n_splits=n_splits)
    oof_proba: NDArray[np.float64] = np.zeros(shape=(len(y),), dtype=np.float64)
    models: List[CalibratedClassifierCV] = []

    for _fold, (trn_idx, val_idx) in enumerate(tscv.split(X), start=1):
        X_trn, y_trn = X[trn_idx], y[trn_idx]
        X_val, y_val = X[val_idx], y[val_idx]

        base = HistGradientBoostingClassifier(
            max_depth=None,
            max_iter=600,
            learning_rate=0.05,
            l2_regularization=1e-2,
            random_state=42,
        )
        w_trn = compute_sample_weights(y_trn)
        base.fit(X_trn, y_trn, sample_weight=w_trn)

        # Calibrate probabilities on validation slice
        cal = CalibratedClassifierCV(base, method="isotonic", cv="prefit")
        _ = cal.fit(X_val, y_val)
        proba: NDArray[np.float64] = cast(NDArray[np.float64], cal.predict_proba(X_val)[:, 1])
        oof_proba[val_idx] = proba
        models.append(cal)

    acc = float(accuracy_score(y, (oof_proba >= 0.5).astype(int)))
    try:
        auc = float(roc_auc_score(y, oof_proba))
    except ValueError:
        auc = float("nan")
    return models, {"accuracy": acc, "auc": auc}


def main():
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--merged_csv", default=Paths().merged_csv)
    _ = parser.add_argument("--model_out", default=Paths().cls_model_file)
    _ = parser.add_argument("--meta_out", default=Paths().cls_model_meta)
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

    os.makedirs(os.path.dirname(model_out), exist_ok=True)
    _ = joblib.dump({"models": models, "feature_cols": feature_cols}, model_out)

    with open(meta_out, "w") as f:
        json.dump({"metrics": metrics, "num_rows": int(df_ready.shape[0]), "trained_at": datetime.now(timezone.utc).isoformat()}, f, indent=2)

    print(json.dumps({"metrics": metrics, "model": model_out, "meta": meta_out}, indent=2))


if __name__ == "__main__":
    main() 