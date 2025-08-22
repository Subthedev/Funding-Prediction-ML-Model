import os
from dataclasses import dataclass


HL_INFO_URL = "https://api.hyperliquid.xyz/info"
DEFAULT_COIN = "HYPE"
DEFAULT_INTERVAL = "1h"
DEFAULT_HISTORY_DAYS = 180
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "data"))
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "models"))


@dataclass
class Paths:
    data_dir: str = DATA_DIR
    models_dir: str = MODELS_DIR
    funding_csv: str = os.path.join(DATA_DIR, "hype_funding.csv")
    candles_csv: str = os.path.join(DATA_DIR, f"hype_candles_{DEFAULT_INTERVAL}.csv")
    merged_csv: str = os.path.join(DATA_DIR, "hype_merged.csv")
    model_file: str = os.path.join(MODELS_DIR, "hype_funding_model.pkl")
    model_meta: str = os.path.join(MODELS_DIR, "hype_funding_model_meta.json")
    cls_model_file: str = os.path.join(MODELS_DIR, "hype_funding_cls_model.pkl")
    cls_model_meta: str = os.path.join(MODELS_DIR, "hype_funding_cls_model_meta.json")
    predictions_log: str = os.path.join(DATA_DIR, "predictions_log.csv") 