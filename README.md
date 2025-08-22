# HYPE Funding Rate Prediction

Predict next funding rate for HYPE perpetuals on Hyperliquid.

## Quickstart

1. Create venv and install deps

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Or with uv + Python 3.11 (recommended for smooth wheels):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv venv -p 3.11 .uvenv
source .uvenv/bin/activate
uv pip install -r requirements.txt
```

2. Fetch data (funding history + candles)

```bash
python -m src.fetch_data --coin HYPE --interval 1h --days 180
```

3. Train regression model (optional)

```bash
python -m src.train
python -m src.infer
```

4. Train classification model (directional signal)

```bash
python -m src.train_cls
```

5. Inference (direction + probability)

```bash
python -m src.infer_cls
```

Outputs are written to `data/` and `models/`. 