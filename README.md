# HYPE Funding Rate Prediction

Predict next funding direction for HYPE on Hyperliquid and expose an actionable dashboard.

## Local quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py  # opens on http://127.0.0.1:7860 (or printed PORT)
```

## Deploy to Hugging Face Spaces (Flask)

1. Create a new Space (type: **Static/Other**, recommended SDK: **Docker/Spaces** or **Python - Gradio** with custom start). Choose "Blank".
2. Push these files to the Space repo: `app.py`, `requirements.txt`, `Procfile`, `templates/` and the `src/` folder with models.
3. In Space settings (or Space README), set the start command to use Gunicorn via Procfile or set:  
   `python app.py`
4. Ensure the following environment variables (optional):
   - `PORT` (HF sets this automatically)
   - `HOST=0.0.0.0`
5. Commit and wait for the build.

The Flask entrypoint is `app:app` and binds to `$PORT` or `7860` locally.

## API

- `GET /api/summary` → JSON containing:
  - `predictedFundingRate` { `pred_next_funding`, `pred_std`, `n_models` }
  - `predictedDirection` { `direction`, `prob_positive`, `confidence`, `n_models` }
  - `liveFunding` { `funding`, `premium`, `markPx`, `oraclePx`, `openInterest` }
  - `nextFundingTime` (ms), `serverTime` (ms)

## UI

- Visit `/dashboard` for the actionable minimal UI with countdown and suggestions. 