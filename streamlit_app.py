import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timezone
import requests
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Page config
st.set_page_config(
    page_title="HYPE Neural Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for futuristic theme
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
        backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        margin: 10px 0;
    }
    
    .prediction-card {
        background: rgba(20, 20, 32, 0.9);
        border: 1px solid rgba(0, 255, 157, 0.3);
        border-radius: 16px;
        padding: 30px;
        backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        margin: 20px 0;
        position: relative;
        overflow: hidden;
    }
    
    .prediction-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #00ff9d, #3742fa, #a55eea);
        animation: shimmer 3s infinite;
    }
    
    @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    
    .funding-explanation {
        background: rgba(20, 20, 32, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
    }
    
    .status-indicator {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: rgba(0, 255, 157, 0.2);
        border: 1px solid #00ff9d;
        border-radius: 20px;
        color: #00ff9d;
        font-weight: 600;
        font-size: 14px;
    }
    
    .pulse-dot {
        width: 8px;
        height: 8px;
        background: #00ff9d;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    h1, h2, h3 {
        color: #ffffff !important;
    }
    
    .stMetric > label {
        color: #a0a0b0 !important;
    }
    
    .stMetric > div {
        color: #ffffff !important;
    }
    
    .big-prediction {
        font-size: 48px !important;
        font-weight: 900 !important;
        text-align: center;
        margin: 20px 0;
        text-shadow: 0 0 20px currentColor;
    }
    
    .direction-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 12px 20px;
        border-radius: 25px;
        font-weight: 700;
        font-size: 16px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin: 10px 0;
    }
    
    .direction-positive {
        background: rgba(0, 255, 157, 0.2);
        color: #00ff9d;
        border: 2px solid #00ff9d;
    }
    
    .direction-negative {
        background: rgba(255, 71, 87, 0.2);
        color: #ff4757;
        border: 2px solid #ff4757;
    }
</style>
""", unsafe_allow_html=True)

# Mock data function
@st.cache_data(ttl=60)
def get_mock_data():
    """Generate mock data for demo purposes"""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "predictedDirection": {
            "direction": "positive",
            "prob_positive": 0.73,
            "confidence": 0.73,
            "n_models": 5
        },
        "predictedFundingRate": {
            "pred_next_funding": 0.00012345,
            "pred_std": 0.000001,
            "n_models": 5
        },
        "liveFunding": {
            "funding": 0.00008765,
            "premium": 0.00001234,
            "markPx": 32.45,
            "oraclePx": 32.44
        },
        "accuracy": {
            "count": 25,
            "correct": 17,
            "accuracy": 0.68
        },
        "nextFundingTime": now_ms + 2400000,  # 40 minutes from now
        "coin": "HYPE",
        "serverTime": now_ms
    }

# Data fetching function
def fetch_api_data():
    """Try to fetch real data, fallback to mock data"""
    try:
        # Try to fetch from local API if running
        response = requests.get("http://localhost:8000/api/summary", timeout=2)
        if response.status_code == 200:
            return response.json(), False
    except:
        pass
    
    # Return mock data
    return get_mock_data(), True

# Utility functions
def format_number(value, decimals=6):
    """Format number with specified decimals"""
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{decimals}f}"

def format_percentage(value):
    """Format as percentage"""
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value) * 100:.1f}%"

def get_countdown_time(next_funding_ms, server_offset=0):
    """Calculate countdown to next funding"""
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

# Generate sample chart data
@st.cache_data(ttl=300)
def generate_chart_data():
    """Generate sample funding rate history"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
    funding_rates = np.random.normal(0.0001, 0.00005, 100)
    
    return pd.DataFrame({
        'timestamp': dates,
        'funding_rate': funding_rates,
        'cumulative': np.cumsum(funding_rates)
    })

# Main app
def main():
    # Header
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 30px;">
            <div style="width: 50px; height: 50px; background: linear-gradient(135deg, #00ff9d, #3742fa); 
                        border-radius: 15px; display: flex; align-items: center; justify-content: center; 
                        font-size: 24px; box-shadow: 0 4px 20px rgba(0, 255, 157, 0.3);">⚡</div>
            <div>
                <h1 style="margin: 0; font-size: 32px; font-weight: 900; 
                           background: linear-gradient(135deg, #00ff9d, #3742fa); 
                           -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    HYPE Neural Dashboard
                </h1>
                <p style="margin: 0; color: #a0a0b0; font-size: 16px;">
                    AI-Powered Funding Rate Predictions
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="status-indicator">
            <div class="pulse-dot"></div>
            <span>LIVE DEMO</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Fetch data
    data, is_mock = fetch_api_data()
    
    if is_mock:
        st.info("🚧 Demo Mode: Using simulated data. Deploy with real ML models for live predictions.")
    
    # Main prediction section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="prediction-card">', unsafe_allow_html=True)
        
        direction = data.get("predictedDirection", {}).get("direction", "unknown")
        probability = data.get("predictedDirection", {}).get("prob_positive", 0.5)
        
        # Determine funding recipient
        if direction == "positive":
            funding_text = "💰 SHORTS RECEIVE FUNDING"
            funding_color = "#00ff9d"
            explanation = "Positive funding rate → Longs pay Shorts"
            badge_class = "direction-positive"
        elif direction == "negative":
            funding_text = "💸 LONGS RECEIVE FUNDING"
            funding_color = "#ff4757"
            explanation = "Negative funding rate → Shorts pay Longs"
            badge_class = "direction-negative"
        else:
            funding_text = "⏳ FUNDING DIRECTION UNCLEAR"
            funding_color = "#a0a0b0"
            explanation = "Unable to predict funding direction"
            badge_class = "direction-negative"
        
        st.markdown("### 🔮 Funding Rate Prediction")
        st.markdown("**Who will receive the next funding payment?**")
        
        st.markdown(f"""
        <div class="big-prediction" style="color: {funding_color};">
            {funding_text}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="direction-badge {badge_class}">
            {direction.upper()} RATE • {format_percentage(probability)} confidence
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="color: #a0a0b0; font-size: 16px; margin: 15px 0; font-weight: 500;">
            {explanation}
        </div>
        """, unsafe_allow_html=True)
        
        # Action buttons
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.link_button("🚀 Trade on Hyperliquid", "https://app.hyperliquid.xyz/perps/HYPE")
        with col_btn2:
            if st.button("🔄 Refresh Data"):
                st.cache_data.clear()
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### ⏰ Next Funding In")
        
        # Countdown (placeholder - would need JavaScript for real-time)
        countdown = get_countdown_time(
            data.get("nextFundingTime"), 
            data.get("_serverOffset", 0)
        )
        
        st.markdown(f"""
        <div style="font-size: 36px; font-weight: 800; color: #3742fa; 
                    text-align: center; font-family: monospace; margin: 20px 0;">
            {countdown}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="text-align: center; color: #a0a0b0; font-size: 14px;">
            Funding occurs every hour
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Funding explanation
    st.markdown("""
    <div class="funding-explanation">
        <h3 style="color: #00ff9d; margin-bottom: 15px;">📚 How Funding Works</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; font-size: 14px; color: #a0a0b0;">
            <div>
                <strong style="color: #00ff9d;">Positive Funding Rate:</strong><br>
                • Longs pay Shorts<br>
                • Shorts receive funding<br>
                • Market is bullish/overheated
            </div>
            <div>
                <strong style="color: #ff4757;">Negative Funding Rate:</strong><br>
                • Shorts pay Longs<br>
                • Longs receive funding<br>
                • Market is bearish/oversold
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Metrics grid
    st.markdown("### 📊 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        predicted_rate = data.get("predictedFundingRate", {}).get("pred_next_funding")
        st.metric(
            "🎯 Predicted Rate",
            format_number(predicted_rate, 8),
            help="AI predicted next funding rate"
        )
    
    with col2:
        current_rate = data.get("liveFunding", {}).get("funding")
        st.metric(
            "📊 Current Rate", 
            format_number(current_rate, 6),
            help="Current live funding rate"
        )
    
    with col3:
        accuracy = data.get("accuracy", {}).get("accuracy")
        st.metric(
            "🏆 Model Accuracy",
            format_percentage(accuracy) if accuracy else "N/A",
            help="Historical prediction accuracy"
        )
    
    with col4:
        n_models = data.get("predictedDirection", {}).get("n_models", 5)
        st.metric(
            "🧠 Neural Models",
            str(n_models),
            help="Number of ensemble models"
        )
    
    # Charts section
    st.markdown("### 📈 Funding Rate History")
    
    # Generate sample chart
    chart_data = generate_chart_data()
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Funding Rate Over Time', 'Cumulative Funding'),
        vertical_spacing=0.1
    )
    
    # Funding rate line chart
    fig.add_trace(
        go.Scatter(
            x=chart_data['timestamp'],
            y=chart_data['funding_rate'],
            mode='lines',
            name='Funding Rate',
            line=dict(color='#00ff9d', width=2)
        ),
        row=1, col=1
    )
    
    # Cumulative funding
    fig.add_trace(
        go.Scatter(
            x=chart_data['timestamp'],
            y=chart_data['cumulative'],
            mode='lines',
            name='Cumulative',
            line=dict(color='#3742fa', width=2),
            fill='tonexty'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=500,
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white')
    )
    
    fig.update_xaxes(gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Additional info
    with st.expander("ℹ️ About This Dashboard"):
        st.markdown("""
        **HYPE Neural Dashboard** uses advanced machine learning models to predict funding rate directions on Hyperliquid.
        
        **Features:**
        - 🤖 Ensemble of 5 neural network models
        - 📊 Real-time market data integration
        - 🎯 Direction prediction with confidence scores
        - 📈 Historical performance tracking
        - ⚡ Live countdown to next funding event
        
        **How to Use:**
        1. Check the main prediction panel for funding direction
        2. Review confidence levels and model consensus
        3. Use the "Trade on Hyperliquid" button to execute trades
        4. Monitor accuracy metrics for model performance
        
        **Disclaimer:** This is for educational purposes. Always do your own research before trading.
        """)

if __name__ == "__main__":
    main()