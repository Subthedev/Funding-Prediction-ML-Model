import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import sys
import joblib
from datetime import datetime, timezone
import requests
import plotly.graph_objects as go

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.hyperliquid_api import get_current_funding_for_coin, get_predicted_funding_for_coin
    from src.features import build_features
    from src.config import Paths
except ImportError:
    # Fallback if src imports fail
    get_current_funding_for_coin = None
    get_predicted_funding_for_coin = None
    build_features = None
    Paths = None

# Page config
st.set_page_config(
    page_title="HYPE Neural Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #0a0a0f 0%, #0f0f17 50%, #141420 100%);
    }
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #0f0f17 50%, #141420 100%);
    }
    .metric-card {
        background: rgba(20, 20, 32, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
    }
    .prediction-card {
        background: rgba(20, 20, 32, 0.9);
        border: 1px solid rgba(0, 255, 157, 0.3);
        border-radius: 16px;
        padding: 30px;
        margin: 20px 0;
    }
    .big-prediction {
        font-size: 48px !important;
        font-weight: 900 !important;
        text-align: center;
        margin: 20px 0;
    }
    h1, h2, h3 {
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

def get_live_funding_data(coin="HYPE"):
    """Fetch live funding data from Hyperliquid"""
    try:
        if get_current_funding_for_coin:
            return get_current_funding_for_coin(coin)
    except Exception as e:
        st.error(f"Error fetching live data: {e}")
    return None

def get_live_predictions(coin="HYPE"):
    """Get live ML predictions"""
    try:
        if not Paths:
            return None
            
        paths = Paths()
        model_file = paths.cls_model_file
        merged_csv = paths.merged_csv
        
        if not os.path.exists(model_file) or not os.path.exists(merged_csv):
            return None
            
        # Load model
        payload = joblib.load(model_file)
        models = payload["models"]
        feature_cols = payload["feature_cols"]
        
        # Load and process data
        df = pd.read_csv(merged_csv)
        if build_features:
            df_feat = build_features(df)
            df_ready = df_feat.copy().dropna().reset_index(drop=True)
            
            if not df_ready.empty:
                x_row = df_ready[feature_cols].astype(float).values[-1:]
                probas = np.array([m.predict_proba(x_row)[0, 1] for m in models])
                p_mean = float(np.mean(probas))
                direction = "positive" if p_mean >= 0.5 else "negative"
                confidence = p_mean if direction == "positive" else (1.0 - p_mean)
                
                return {
                    "direction": direction,
                    "prob_positive": p_mean,
                    "confidence": confidence,
                    "n_models": len(models)
                }
    except Exception as e:
        st.error(f"Error getting predictions: {e}")
    return None

@st.cache_data(ttl=60)
def get_mock_data():
    """Generate mock data as fallback"""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "predictedDirection": {
            "direction": "positive",
            "prob_positive": 0.73,
            "confidence": 0.73,
            "n_models": 5
        },
        "liveFunding": {
            "funding": 0.00008765,
            "markPx": 32.45,
        },
        "accuracy": {
            "count": 25,
            "correct": 17,
            "accuracy": 0.68
        },
        "nextFundingTime": now_ms + 2400000,
        "coin": "HYPE"
    }

def fetch_api_data():
    """Fetch live data with fallbacks"""
    # Try to get live data
    live_funding = get_live_funding_data()
    live_predictions = get_live_predictions()
    
    if live_funding or live_predictions:
        # Calculate next funding time (hourly on Hyperliquid)
        now = datetime.now(timezone.utc)
        next_hour = now.replace(minute=0, second=0, microsecond=0) + pd.Timedelta(hours=1)
        next_funding_ms = int(next_hour.timestamp() * 1000)
        
        data = {
            "coin": "HYPE",
            "nextFundingTime": next_funding_ms,
            "serverTime": int(now.timestamp() * 1000)
        }
        
        if live_predictions:
            data["predictedDirection"] = live_predictions
        else:
            data["predictedDirection"] = {
                "direction": "unknown",
                "prob_positive": 0.5,
                "confidence": 0.5,
                "n_models": 0
            }
            
        if live_funding:
            data["liveFunding"] = live_funding
        else:
            data["liveFunding"] = {"funding": 0, "markPx": 0}
            
        # Mock accuracy for now
        data["accuracy"] = {"count": 0, "correct": 0, "accuracy": 0}
        
        return data, False
    
    # Fallback to mock data
    return get_mock_data(), True

def format_number(value, decimals=6):
    """Format number"""
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{decimals}f}"

def format_percentage(value):
    """Format percentage"""
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value) * 100:.1f}%"

def get_countdown_time(next_funding_ms, server_offset=0):
    """Calculate countdown"""
    if not next_funding_ms:
        return "--:--:--"
    
    now_ms = int(time.time() * 1000) + server_offset
    remaining = max(0, next_funding_ms - now_ms)
    
    hours = remaining // 3600000
    remaining %= 3600000
    minutes = remaining // 60000
    remaining %= 60000
    seconds = remaining // 1000
    
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

@st.cache_data(ttl=300)
def get_funding_history():
    """Get funding rate history"""
    try:
        if Paths:
            paths = Paths()
            if os.path.exists(paths.funding_csv):
                df = pd.read_csv(paths.funding_csv)
                if 'time' in df.columns and 'funding' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
                    return df[['timestamp', 'funding']].tail(100)
    except Exception:
        pass
    
    # Fallback to mock data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
    funding_rates = np.random.normal(0.0001, 0.00005, 100)
    
    return pd.DataFrame({
        'timestamp': dates,
        'funding': funding_rates
    })

def main():
    # Header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="font-size: 48px; margin: 0;">⚡ HYPE Neural Dashboard</h1>
        <p style="color: #a0a0b0; font-size: 18px;">AI-Powered Funding Rate Predictions</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Fetch data
    data, is_mock = fetch_api_data()
    
    if is_mock:
        st.warning("🚧 Demo Mode: Using simulated data. Live ML models not available.")
    else:
        st.success("🔴 LIVE: Real-time data from Hyperliquid")
    
    # Main prediction section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="prediction-card">', unsafe_allow_html=True)
        
        direction = data.get("predictedDirection", {}).get("direction", "unknown")
        probability = data.get("predictedDirection", {}).get("prob_positive", 0.5)
        
        if direction == "positive":
            funding_text = "💰 SHORTS RECEIVE FUNDING"
            funding_color = "#00ff9d"
            explanation = "Positive funding rate → Longs pay Shorts"
        elif direction == "negative":
            funding_text = "💸 LONGS RECEIVE FUNDING"
            funding_color = "#ff4757"
            explanation = "Negative funding rate → Shorts pay Longs"
        else:
            funding_text = "⏳ FUNDING DIRECTION UNCLEAR"
            funding_color = "#a0a0b0"
            explanation = "Unable to predict funding direction"
        
        st.markdown("### 🔮 Funding Rate Prediction")
        st.markdown("**Who will receive the next funding payment?**")
        
        st.markdown(f"""
        <div class="big-prediction" style="color: {funding_color};">
            {funding_text}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"**Confidence:** {format_percentage(probability)}")
        st.markdown(f"*{explanation}*")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### ⏰ Next Funding")
        
        countdown = get_countdown_time(data.get("nextFundingTime", 0))
        st.markdown(f"**Time Remaining:** `{countdown}`")
        
        current_funding = data.get("liveFunding", {}).get("funding", 0)
        st.markdown(f"**Current Rate:** `{format_number(current_funding, 6)}`")
        
        mark_price = data.get("liveFunding", {}).get("markPx", 0)
        st.markdown(f"**Mark Price:** `${format_number(mark_price, 2)}`")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Performance metrics
    st.markdown("### 📊 Model Performance")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        accuracy = data.get("accuracy", {}).get("accuracy", 0)
        st.metric("Accuracy", format_percentage(accuracy))
    
    with col2:
        predictions_count = data.get("accuracy", {}).get("count", 0)
        st.metric("Predictions Made", predictions_count)
    
    with col3:
        correct_count = data.get("accuracy", {}).get("correct", 0)
        st.metric("Correct Predictions", correct_count)
    
    # Chart section
    st.markdown("### 📈 Funding Rate History")
    
    chart_data = get_funding_history()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart_data['timestamp'],
        y=chart_data['funding'],
        mode='lines',
        name='Funding Rate',
        line=dict(color='#00ff9d', width=2)
    ))
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Explanation
    st.markdown("""
    ### 💡 How Funding Rates Work
    - **Positive Rate:** Longs pay Shorts (bullish sentiment)
    - **Negative Rate:** Shorts pay Longs (bearish sentiment)  
    - **Payment Time:** Every hour on Hyperliquid
    """)

if __name__ == "__main__":
    main()