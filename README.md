# HYPE Funding Rate Prediction

Predict next funding direction for HYPE on Hyperliquid and expose an actionable dashboard.

## Local quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py  # opens on http://127.0.0.1:7860 (or printed PORT)
```

## Deploy to Hugging Face Spaces (Flask)

Option A — Manual upload
1. Create a new Space (type: "Other"/Blank).
2. Upload `app.py`, `requirements.txt`, `Procfile`, `templates/`, and the `src/` folder (and any trained models under `models/`).
3. Spaces picks up `Procfile` automatically (entrypoint: `gunicorn app:app`).

Option B — GitHub Actions (auto-deploy)
1. Create a Space on Hugging Face and copy its Space ID, e.g. `username/hype-funding-dashboard`.
2. In your GitHub repo, add Secrets:
   - `HF_TOKEN`: a User Access Token with write access.
   - `HF_SPACE_ID`: the Space ID string, e.g. `username/hype-funding-dashboard`.
3. The workflow `.github/workflows/hf-deploy.yml` uploads the app on pushes to `main` or `feature/hf-space`.

## API

- `GET /api/summary` → JSON containing:
  - `predictedFundingRate` { `pred_next_funding`, `pred_std`, `n_models` }
  - `predictedDirection` { `direction`, `prob_positive`, `confidence`, `n_models` }
  - `liveFunding` { `funding`, `premium`, `markPx`, `oraclePx`, `openInterest` }
  - `nextFundingTime` (ms), `serverTime` (ms)

## UI

- Visit `/dashboard` for the actionable minimal UI with countdown and suggestions. 