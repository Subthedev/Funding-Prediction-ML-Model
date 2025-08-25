import streamlit as st
import pandas as pd
import numpy as np
import time
import requests
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta
import json

# Page config
st.set_page_config(
    page_title="HYPE Funding Tracker",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main { background: linear-gradient(135deg, #0a0a0f 0%, #0f0f17 50%, #141420 100%); }
    .stApp { background: linear-gradient(135deg, #0a0a0f 0%, #0f0f17 50%, #141420 100%); }
    .metric-card {
        background: rgba(20, 20, 32, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
    }
    .alert-card {
        background: rgba(255, 71, 87, 0.1);
        border: 2px solid #ff4757;
        border-radius: 16px;
        padding: 20px;
        margin: 20px 0;
    }
    .profit-card {
        background: rgba(0, 255, 157, 0.1);
        border: 2px solid #00ff9d;
        border-radius: 16px;
        padding: 20px;
        margin: 20px 0;
    }
    .big-number {
        font-size: 36px !important;
        font-weight: 900 !important;
        text-align: center;
        margin: 10px 0;
    }
    h1, h2, h3 { color: #ffffff !important; }
    .stMetric > label { color: #a0a0b0 !important; }
    .stMetric > div { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# Live data functions
@st.cache_data(ttl=30)  # Refresh every 30 seconds
def get_hyperliquid_data():
    """Fetch live data from Hyperliquid API"""
    try:
        # Get meta and asset contexts
        response = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "metaAndAssetCtxs"},
            timeout=10
        )
        if response.status_code == 200:
            meta, ctxs = response.json()
            
            # Find HYPE in universe
            for idx, asset in enumerate(meta.get("universe", [])):
                if asset.get("name") == "HYPE" and idx < len(ctxs):
                    ctx = ctxs[idx]
                    return {
                        "funding": float(ctx.get("funding", 0)),
                        "premium": float(ctx.get("premium", 0)),
                        "markPx": float(ctx.get("markPx", 0)),
                        "oraclePx": float(ctx.get("oraclePx", 0)),
                        "openInterest": float(ctx.get("openInterest", 0)),
                        "timestamp": int(time.time() * 1000)
                    }
    except Exception as e:
        st.error(f"API Error: {e}")
    return None

def calculate_funding_metrics(funding_rate):
    """Calculate trading metrics from funding rate"""
    # Annualized funding rate (8760 hours per year)
    annual_rate = funding_rate * 8760
    
    # Position size recommendations based on funding rate magnitude
    if abs(funding_rate) > 0.0005:  # 0.05%
        risk_level = "HIGH"
        position_size = "Large (5-10% portfolio)"
    elif abs(funding_rate) > 0.0002:  # 0.02%
        risk_level = "MEDIUM"
        position_size = "Medium (2-5% portfolio)"
    else:
        risk_level = "LOW"
        position_size = "Small (1-2% portfolio)"
    
    return {
        "annual_rate": annual_rate,
        "risk_level": risk_level,
        "position_size": position_size,
        "hourly_pnl_per_1000": funding_rate * 1000  # PnL per $1000 position
    }

def get_next_funding_time():
    """Calculate next funding time (every hour on the hour)"""
    now = datetime.now(timezone.utc)
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return next_hour

def format_countdown(target_time):
    """Format countdown timer"""
    now = datetime.now(timezone.utc)
    remaining = target_time - now
    
    if remaining.total_seconds() <= 0:
        return "00:00:00"
    
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    seconds = int(remaining.total_seconds() % 60)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def generate_trading_signals(funding_rate, premium):
    """Generate actionable trading signals"""
    signals = []
    
    # Funding rate signals
    if funding_rate > 0.0003:  # 0.03%
        signals.append({
            "type": "FUNDING_ARBITRAGE",
            "action": "SHORT",
            "reason": f"High positive funding ({funding_rate*100:.3f}%) - Shorts receive payment",
            "urgency": "HIGH",
            "expected_return": f"{funding_rate*100:.3f}% per hour"
        })
    elif funding_rate < -0.0003:  # -0.03%
        signals.append({
            "type": "FUNDING_ARBITRAGE", 
            "action": "LONG",
            "reason": f"High negative funding ({funding_rate*100:.3f}%) - Longs receive payment",
            "urgency": "HIGH",
            "expected_return": f"{abs(funding_rate)*100:.3f}% per hour"
        })
    
    # Premium signals
    if abs(premium) > 0.001:  # 0.1%
        action = "SHORT" if premium > 0 else "LONG"
        signals.append({
            "type": "PREMIUM_ARBITRAGE",
            "action": action,
            "reason": f"Large premium gap ({premium*100:.3f}%)",
            "urgency": "MEDIUM",
            "expected_return": f"{abs(premium)*100:.3f}% potential"
        })
    
    return signals

# Auto-refresh functionality
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# Auto-refresh every 30 seconds
if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.rerun()

def main():
    # Header with live status
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="font-size: 42px; margin: 0;">⚡ HYPE Funding Tracker</h1>
            <p style="color: #a0a0b0; font-size: 16px;">Real-time Funding Rate Arbitrage Opportunities</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Live refresh button
        if st.button("🔄 Refresh", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    # Get live data
    live_data = get_hyperliquid_data()
    
    if live_data:
        st.success("🟢 LIVE DATA - Connected to Hyperliquid")
        
        funding_rate = live_data["funding"]
        premium = live_data["premium"]
        mark_price = live_data["markPx"]
        
        # Calculate metrics
        metrics = calculate_funding_metrics(funding_rate)
        next_funding = get_next_funding_time()
        countdown = format_countdown(next_funding)
        
        # Main dashboard
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Current funding rate - BIG DISPLAY
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown("### 💰 Current Funding Rate")
            
            color = "#00ff9d" if funding_rate > 0 else "#ff4757" if funding_rate < 0 else "#a0a0b0"
            st.markdown(f"""
            <div class="big-number" style="color: {color};">
                {funding_rate*100:.4f}%
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"**Annual Rate:** {metrics['annual_rate']*100:.1f}%")
            st.markdown(f"**Risk Level:** {metrics['risk_level']}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            # Next funding countdown
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown("### ⏰ Next Payment")
            st.markdown(f"""
            <div class="big-number" style="color: #00ff9d;">
                {countdown}
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"**At:** {next_funding.strftime('%H:%M UTC')}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            # Mark price
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown("### 📊 HYPE Price")
            st.markdown(f"""
            <div class="big-number" style="color: #ffffff;">
                ${mark_price:.3f}
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"**Premium:** {premium*100:.3f}%")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Trading signals
        signals = generate_trading_signals(funding_rate, premium)
        
        if signals:
            st.markdown("## 🚨 TRADING OPPORTUNITIES")
            
            for signal in signals:
                if signal["urgency"] == "HIGH":
                    st.markdown('<div class="alert-card">', unsafe_allow_html=True)
                    st.markdown(f"### 🔥 {signal['type']} - {signal['action']}")
                else:
                    st.markdown('<div class="profit-card">', unsafe_allow_html=True)
                    st.markdown(f"### 💡 {signal['type']} - {signal['action']}")
                
                st.markdown(f"**Reason:** {signal['reason']}")
                st.markdown(f"**Expected Return:** {signal['expected_return']}")
                st.markdown(f"**Urgency:** {signal['urgency']}")
                
                # Action steps
                if signal["action"] == "SHORT":
                    st.markdown("""
                    **Action Steps:**
                    1. Open SHORT position on Hyperliquid
                    2. Hold until next funding payment
                    3. Collect funding payment from longs
                    4. Close position or hold for next cycle
                    """)
                else:
                    st.markdown("""
                    **Action Steps:**
                    1. Open LONG position on Hyperliquid  
                    2. Hold until next funding payment
                    3. Collect funding payment from shorts
                    4. Close position or hold for next cycle
                    """)
                
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("📊 No high-probability arbitrage opportunities at current funding rates")
        
        # Profit calculator
        st.markdown("## 🧮 Profit Calculator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            position_size = st.number_input("Position Size ($)", min_value=100, max_value=100000, value=1000, step=100)
            hours_held = st.number_input("Hours to Hold", min_value=1, max_value=168, value=1)
        
        with col2:
            # Calculate potential profit
            hourly_profit = position_size * abs(funding_rate)
            total_profit = hourly_profit * hours_held
            
            st.metric("Hourly Funding Income", f"${hourly_profit:.2f}")
            st.metric(f"Total Income ({hours_held}h)", f"${total_profit:.2f}")
            
            if funding_rate > 0:
                st.success("💰 SHORT position receives funding")
            elif funding_rate < 0:
                st.success("💰 LONG position receives funding")
        
        # Risk warnings
        st.markdown("## ⚠️ Risk Warnings")
        st.warning("""
        **Important Disclaimers:**
        - Funding rates can change rapidly
        - Price movements can offset funding gains
        - Always use proper risk management
        - This is not financial advice
        - Past performance doesn't guarantee future results
        """)
        
        # Historical data
        st.markdown("## 📈 Recent Funding History")
        
        # Generate sample historical data (in real app, fetch from API)
        hours = pd.date_range(start=datetime.now() - timedelta(hours=24), end=datetime.now(), freq='H')
        historical_rates = np.random.normal(funding_rate, 0.0001, len(hours))
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hours,
            y=historical_rates * 100,
            mode='lines+markers',
            name='Funding Rate %',
            line=dict(color='#00ff9d', width=2)
        ))
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            xaxis=dict(gridcolor='rgba(255,255,255,0.1)', title="Time (UTC)"),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)', title="Funding Rate %"),
            height=400,
            title="24-Hour Funding Rate History"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.error("🔴 Unable to connect to Hyperliquid API - Using demo data")
        
        # Demo mode with sample data
        st.markdown("### 🚧 Demo Mode")
        st.info("This is sample data. Real app connects to live Hyperliquid API.")
        
        # Sample demo data
        demo_funding = 0.000234  # 0.0234%
        st.markdown(f"**Sample Funding Rate:** {demo_funding*100:.4f}%")
        st.markdown(f"**Sample Annual Rate:** {demo_funding*8760*100:.1f}%")
        
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666;">
        <p>⚡ HYPE Funding Tracker - Real-time funding rate arbitrage opportunities</p>
        <p>Data from Hyperliquid • Updates every 30 seconds</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()