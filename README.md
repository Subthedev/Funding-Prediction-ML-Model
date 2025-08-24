# HYPE Funding Rate Prediction

ML model to predict the next hourly funding rate direction for HYPE token on Hyperliquid.

## Quick Start

### Local Development

1. **Setup Environment**:
```bash
# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment with Python 3.11
uv venv .uvenv --python 3.11
source .uvenv/bin/activate  # On Windows: .uvenv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt
```

2. **Fetch Initial Data**:
```bash
python src/fetch_data.py --coin HYPE --days 30
```

3. **Train Models**:
```bash
python src/train_cls.py  # Classification model (direction prediction)
python src/train.py      # Regression model (exact rate prediction)
```

4. **Run Web Dashboard**:
```bash
python app.py
```

Visit `http://localhost:8000/dashboard` for the interactive UI.

## Deployment

### Deploy to Render (Recommended)

1. **Fork and Connect Repository**:
   - Fork this repository to your GitHub
   - Sign up at [render.com](https://render.com)
   - Connect your GitHub account

2. **Create Web Service**:
   - Click "New +" → "Web Service"
   - Connect your forked repository
   - Choose branch: `main` or `feature/render-deploy`

3. **Configuration** (Auto-detected from `render.yaml`):
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --timeout 120 --workers 1 --threads 2 --bind 0.0.0.0:$PORT`
   - **Python Version**: 3.11.4

4. **Deploy**:
   - Click "Create Web Service"
   - Wait for build and deployment (~3-5 minutes)
   - Access your app at: `https://your-app-name.onrender.com/dashboard`

### Deploy to Hugging Face Spaces

1. **Automated Deployment (GitHub Actions)**:
   - Add repository secrets:
     - `HF_TOKEN`: Your Hugging Face write token
     - `HF_SPACE_ID`: Your Space ID (e.g., `username/hype-funding-dashboard`)
   - Push to `main` branch to trigger auto-deployment

2. **Manual Deployment**:
   - Create a new Space on Hugging Face (Type: Gradio)
   - Upload: `app.py`, `requirements.txt`, `Procfile`, `templates/`, `src/`
   - The app will start automatically

## Features

- **Real-time Predictions**: Next hourly funding rate direction (Long/Short/Wait)
- **Live Data**: Current funding rate with countdown timer
- **Performance Tracking**: Model accuracy and prediction history
- **Interactive Dashboard**: Clean, actionable UI with real-time updates
- **Hyperliquid Integration**: Live market data and predicted funding rates

## API Endpoints

- `GET /dashboard` - Interactive web dashboard
- `GET /api/summary` - JSON data for predictions, live rates, and accuracy
- `GET /health` - Health check endpoint

## Project Structure

```
src/
├── config.py           # Configuration and constants
├── hyperliquid_api.py  # Hyperliquid API client
├── fetch_data.py       # Data fetching and preprocessing
├── features.py         # Feature engineering
├── train_cls.py        # Classification model training
├── train.py            # Regression model training
├── infer_cls.py        # Classification inference
├── infer.py            # Regression inference
└── live_loop.py        # Live prediction pipeline

templates/
└── dashboard.html      # React-based web dashboard

app.py                  # Flask web application
requirements.txt        # Python dependencies
render.yaml            # Render deployment config
```

## Model Details

- **Classification Model**: HistGradientBoostingClassifier with probability calibration
- **Features**: Price action, volatility, RSI, funding rate history, time-based features
- **Target**: Binary classification (positive/negative funding rate)
- **Evaluation**: Time-series cross-validation with accuracy tracking

## License

MIT License 