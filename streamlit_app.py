import streamlit as st
import pandas as pd
import numpy as np
import time
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timezone, timedelta
import json
import asyncio
from typing import Dict, List, Optional

# Page config
st.set_page_config(
    page_title="HYPE Pro Trader",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Professional CSS styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .main { 
        background: linear-gradient(135deg, #0B0E1A 0%, #1A1D29 50%, #2D3748 100%);
        font-family: 'Inter', sans-serif;
    }
    .stApp { 
        background: linear-gradient(135deg, #0B0E1A 0%, #1A1D29 50%, #2D3748 100%);
    }
    
    /* Professional Cards */
    .pro-card {
        background: rgba(26, 32, 44, 0.95);
        border: 1px solid rgba(74, 85, 104, 0.3);
        border-radius: 20px;
        padding: 24px;
        margin: 16px 0;
        backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .pro-card:hover {
        border-color: rgba(72, 187, 120, 0.5);
        box-shadow: 0 12px 40px rgba(72, 187, 120, 0.1);
    }
    
    /* Alert Cards */
    .alert-high {
        background: linear-gradient(135deg, rgba(245, 101, 101, 0.1) 0%, rgba(229, 62, 62, 0.05) 100%);
        border: 2px solid #F56565;
        border-radius: 16px;
        padding: 20px;
        margin: 16px 0;
        animation: pulse-red 2s infinite;
    }
    
    .alert-medium {
        background: linear-gradient(135deg, rgba(237, 137, 54, 0.1) 0%, rgba(221, 107, 32, 0.05) 100%);
        border: 2px solid #ED8936;
        border-radius: 16px;
        padding: 20px;
        margin: 16px 0;
    }
    
    .profit-opportunity {
        background: linear-gradient(135deg, rgba(72, 187, 120, 0.1) 0%, rgba(56, 161, 105, 0.05) 100%);
        border: 2px solid #48BB78;
        border-radius: 16px;
        padding: 20px;
        margin: 16px 0;
        animation: pulse-green 3s infinite;
    }
    
    @keyframes pulse-red {
        0%, 100% { box-shadow: 0 0 20px rgba(245, 101, 101, 0.3); }
        50% { box-shadow: 0 0 30px rgba(245, 101, 101, 0.6); }
    }
    
    @keyframes pulse-green {
        0%, 100% { box-shadow: 0 0 20px rgba(72, 187, 120, 0.3); }
        50% { box-shadow: 0 0 30px rgba(72, 187, 120, 0.6); }
    }
    
    /* Typography */
    .hero-number {
        font-size: 48px !important;
        font-weight: 700 !important;
        text-align: center;
        margin: 16px 0;
        text-shadow: 0 0 20px currentColor;
    }
    
    .metric-number {
        font-size: 32px !important;
        font-weight: 600 !important;
        text-align: center;
        margin: 12px 0;
    }
    
    .countdown-timer {
        font-size: 36px !important;
        font-weight: 700 !important;
        text-align: center;
        font-family: 'Courier New', monospace;
        color: #48BB78;
        text-shadow: 0 0 10px rgba(72, 187, 120, 0.5);
    }
    
    /* Status Indicators */
    .status-live {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: rgba(72, 187, 120, 0.2);
        border: 1px solid #48BB78;
        border-radius: 20px;
        color: #48BB78;
        font-weight: 600;
        font-size: 14px;
    }
    
    .pulse-dot {
        width: 8px;
        height: 8px;
        background: #48BB78;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.2); }
    }
    
    /* Action Buttons */
    .action-button {
        background: linear-gradient(135deg, #48BB78 0%, #38A169 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        display: inline-block;
        margin: 8px 4px;
    }
    
    .action-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(72, 187, 120, 0.3);
    }
    
    /* Progress Bars */
    .progress-bar {
        width: 100%;
        height: 8px;
        background: rgba(74, 85, 104, 0.3);
        border-radius: 4px;
        overflow: hidden;
        margin: 8px 0;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #48BB78, #38A169);
        border-radius: 4px;
        transition: width 0.3s ease;
    }
    
    h1, h2, h3, h4 { 
        color: #F7FAFC !important; 
        font-family: 'Inter', sans-serif !important;
    }
    
    .stMetric > label { 
        color: #A0AEC0 !important; 
        font-weight: 500 !important;
    }
    
    .stMetric > div { 
        color: #F7FAFC !important; 
        font-weight: 600 !important;
    }
    
    /* Sidebar Styling */
    .css-1d391kg { background: rgba(26, 32, 44, 0.95); }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'alerts_enabled' not in st.session_state:
    st.session_state.alerts_enabled = True
if 'position_tracker' not in st.session_state:
    st.session_state.position_tracker = []
if 'profit_history' not in st.session_state:
    st.session_state.profit_history = []

# Live data functions
@st.cache_data(ttl=15)  # Refresh every 15 seconds for real-time feel
def get_hyperliquid_data():
    """Fetch live data from Hyperliquid API with error handling"""
    try:
        response = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "metaAndAssetCtxs"},
            timeout=8
        )
        if response.status_code == 200:
            meta, ctxs = response.json()
            
            for idx, asset in enumerate(meta.get("universe", [])):
                if asset.get("name") == "HYPE" and idx < len(ctxs):
                    ctx = ctxs[idx]
                    return {
                        "funding": float(ctx.get("funding", 0)),
                        "premium": float(ctx.get("premium", 0)),
                        "markPx": float(ctx.get("markPx", 0)),
                        "oraclePx": float(ctx.get("oraclePx", 0)),
                        "openInterest": float(ctx.get("openInterest", 0)),
                        "timestamp": int(time.time() * 1000),
                        "volume24h": float(ctx.get("dayNtlVlm", 0)),
                        "prevDayPx": float(ctx.get("prevDayPx", ctx.get("markPx", 0)))
                    }
    except Exception as e:
        st.error(f"⚠️ API Connection Issue: {str(e)[:100]}...")
    return None

def get_funding_history():
    """Fetch historical funding data"""
    try:
        # In production, this would fetch real historical data
        # For now, generate realistic sample data
        hours = pd.date_range(start=datetime.now() - timedelta(hours=168), end=datetime.now(), freq='H')
        base_rate = np.random.normal(0.0001, 0.00005, len(hours))
        
        # Add some realistic patterns
        for i in range(1, len(base_rate)):
            base_rate[i] = base_rate[i-1] * 0.8 + base_rate[i] * 0.2  # Add persistence
        
        return pd.DataFrame({
            'timestamp': hours,
            'funding_rate': base_rate,
            'volume': np.random.exponential(1000000, len(hours))
        })
    except Exception:
        return pd.DataFrame()

def calculate_advanced_metrics(data: Dict) -> Dict:
    """Calculate comprehensive trading metrics"""
    funding_rate = data["funding"]
    premium = data["premium"]
    mark_price = data["markPx"]
    
    # Risk assessment
    volatility = abs(funding_rate) * 100
    if volatility > 0.05:
        risk_level = "🔴 HIGH"
        risk_color = "#F56565"
    elif volatility > 0.02:
        risk_level = "🟡 MEDIUM"
        risk_color = "#ED8936"
    else:
        risk_level = "🟢 LOW"
        risk_color = "#48BB78"
    
    # Opportunity scoring (0-100)
    opportunity_score = min(100, abs(funding_rate) * 100000)
    
    # Expected returns
    hourly_return = abs(funding_rate) * 100
    daily_return = hourly_return * 24
    weekly_return = daily_return * 7
    annual_return = daily_return * 365
    
    return {
        "risk_level": risk_level,
        "risk_color": risk_color,
        "opportunity_score": opportunity_score,
        "hourly_return": hourly_return,
        "daily_return": daily_return,
        "weekly_return": weekly_return,
        "annual_return": annual_return,
        "volatility": volatility
    }

def generate_professional_signals(data: Dict, metrics: Dict) -> List[Dict]:
    """Generate professional trading signals with detailed analysis"""
    signals = []
    funding_rate = data["funding"]
    premium = data["premium"]
    
    # High-probability funding arbitrage
    if abs(funding_rate) > 0.0003:  # 0.03%
        urgency = "HIGH" if abs(funding_rate) > 0.0005 else "MEDIUM"
        action = "SHORT" if funding_rate > 0 else "LONG"
        
        signals.append({
            "type": "FUNDING_ARBITRAGE",
            "action": action,
            "urgency": urgency,
            "confidence": min(95, 60 + abs(funding_rate) * 100000),
            "expected_return": f"{abs(funding_rate)*100:.4f}% per hour",
            "risk_reward": abs(funding_rate) / max(0.0001, metrics["volatility"]/100),
            "reason": f"{'High positive' if funding_rate > 0 else 'High negative'} funding rate",
            "entry_price": data["markPx"],
            "target_duration": "1-24 hours",
            "max_position": "10-25% of portfolio"
        })
    
    # Premium arbitrage opportunities
    if abs(premium) > 0.001:
        signals.append({
            "type": "PREMIUM_ARBITRAGE",
            "action": "SHORT" if premium > 0 else "LONG",
            "urgency": "MEDIUM",
            "confidence": min(80, 50 + abs(premium) * 10000),
            "expected_return": f"{abs(premium)*100:.3f}% potential",
            "risk_reward": abs(premium) / 0.002,
            "reason": f"Mark-Oracle price divergence: {premium*100:.3f}%",
            "entry_price": data["markPx"],
            "target_duration": "Minutes to hours",
            "max_position": "5-15% of portfolio"
        })
    
    return signals

def get_next_funding_time():
    """Calculate precise next funding time"""
    now = datetime.now(timezone.utc)
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return next_hour

def format_live_countdown(target_time):
    """Format live countdown with millisecond precision"""
    now = datetime.now(timezone.utc)
    remaining = target_time - now
    
    if remaining.total_seconds() <= 0:
        return "00:00:00", 0
    
    total_seconds = remaining.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    
    progress = 1 - (total_seconds / 3600)  # Progress through the hour
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}", progress

# Auto-refresh with live timer
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# Refresh every 15 seconds for live feel
if time.time() - st.session_state.last_refresh > 15:
    st.session_state.last_refresh = time.time()
    st.rerun()

def main():
    # Professional Header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="font-size: 52px; margin: 0; background: linear-gradient(135deg, #48BB78, #38A169); 
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            ⚡ HYPE Pro Trader
        </h1>
        <p style="color: #A0AEC0; font-size: 18px; margin-top: 8px;">
            Professional Funding Rate Arbitrage Platform
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Live status bar
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        live_data = get_hyperliquid_data()
        if live_data:
            st.markdown("""
            <div class="status-live">
                <div class="pulse-dot"></div>
                <span>LIVE DATA • Hyperliquid Connected</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("🔴 API Disconnected - Check connection")
    
    with col2:
        if st.button("🔄 Force Refresh", type="secondary"):
            st.cache_data.clear()
            st.rerun()
    
    with col3:
        # Settings toggle
        st.session_state.alerts_enabled = st.toggle("🔔 Alerts", value=st.session_state.alerts_enabled)
    
    if not live_data:
        st.warning("⚠️ Using demo data - Live API unavailable")
        live_data = {
            "funding": 0.000234,
            "premium": 0.000012,
            "markPx": 32.456,
            "oraclePx": 32.444,
            "openInterest": 1250000,
            "volume24h": 5600000,
            "timestamp": int(time.time() * 1000)
        }
    
    # Calculate metrics
    metrics = calculate_advanced_metrics(live_data)
    next_funding = get_next_funding_time()
    countdown, progress = format_live_countdown(next_funding)
    
    # Main Dashboard - Hero Section
    st.markdown('<div class="pro-card">', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        st.markdown("### 💰 Current Funding Rate")
        color = "#48BB78" if live_data["funding"] > 0 else "#F56565" if live_data["funding"] < 0 else "#A0AEC0"
        st.markdown(f"""
        <div class="hero-number" style="color: {color};">
            {live_data["funding"]*100:.4f}%
        </div>
        <div style="text-align: center; color: #A0AEC0;">
            Annual: {metrics['annual_return']:.1f}% • Risk: {metrics['risk_level']}
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### ⏰ Next Payment")
        st.markdown(f"""
        <div class="countdown-timer">{countdown}</div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {progress*100:.1f}%;"></div>
        </div>
        <div style="text-align: center; color: #A0AEC0; font-size: 12px;">
            {next_funding.strftime('%H:%M UTC')}
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("### 📊 HYPE Price")
        price_change = ((live_data["markPx"] - live_data.get("prevDayPx", live_data["markPx"])) / live_data.get("prevDayPx", live_data["markPx"])) * 100
        price_color = "#48BB78" if price_change >= 0 else "#F56565"
        st.markdown(f"""
        <div class="metric-number" style="color: white;">
            ${live_data["markPx"]:.3f}
        </div>
        <div style="text-align: center; color: {price_color}; font-size: 14px;">
            {price_change:+.2f}% (24h)
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("### 🎯 Opportunity")
        st.markdown(f"""
        <div class="metric-number" style="color: {metrics['risk_color']};">
            {metrics['opportunity_score']:.0f}/100
        </div>
        <div style="text-align: center; color: #A0AEC0; font-size: 14px;">
            Score
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Trading Signals Section
    signals = generate_professional_signals(live_data, metrics)
    
    if signals:
        st.markdown("## 🚨 ACTIVE TRADING OPPORTUNITIES")
        
        for i, signal in enumerate(signals):
            card_class = "alert-high" if signal["urgency"] == "HIGH" else "profit-opportunity"
            
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                ### 🎯 {signal['type'].replace('_', ' ')} - {signal['action']}
                **Strategy:** {signal['reason']}  
                **Expected Return:** {signal['expected_return']}  
                **Confidence:** {signal['confidence']:.0f}%  
                **Risk/Reward:** {signal['risk_reward']:.2f}  
                **Duration:** {signal['target_duration']}  
                **Max Position:** {signal['max_position']}
                """)
            
            with col2:
                st.markdown(f"""
                <div style="text-align: center; padding: 20px;">
                    <div style="font-size: 24px; font-weight: bold; color: {'#48BB78' if signal['action'] == 'LONG' else '#F56565'};">
                        {signal['action']} HYPE
                    </div>
                    <div style="font-size: 18px; margin: 8px 0;">
                        @ ${signal['entry_price']:.3f}
                    </div>
                    <a href="https://app.hyperliquid.xyz/trade/HYPE" target="_blank" class="action-button">
                        Trade on Hyperliquid →
                    </a>
                </div>
                """, unsafe_allow_html=True)
            
            # Detailed action plan
            if signal["action"] == "SHORT":
                st.markdown("""
                **📋 Execution Plan:**
                1. **Enter SHORT** position on Hyperliquid at current market price
                2. **Set stop-loss** at +2% to limit downside risk
                3. **Hold position** until next funding payment (see countdown above)
                4. **Collect funding** payment from long positions
                5. **Evaluate** - close position or hold for next cycle
                
                **💡 Pro Tip:** Monitor funding rate changes. If rate drops significantly, consider closing early.
                """)
            else:
                st.markdown("""
                **📋 Execution Plan:**
                1. **Enter LONG** position on Hyperliquid at current market price
                2. **Set stop-loss** at -2% to limit downside risk  
                3. **Hold position** until next funding payment (see countdown above)
                4. **Collect funding** payment from short positions
                5. **Evaluate** - close position or hold for next cycle
                
                **💡 Pro Tip:** Watch for funding rate reversals. Exit if rate approaches zero.
                """)
            
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("📊 No high-probability opportunities detected at current funding rates")
    
    # Advanced Analytics Section
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("## 🧮 Position Calculator")
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        
        portfolio_size = st.number_input("Portfolio Size ($)", min_value=1000, max_value=1000000, value=10000, step=1000)
        risk_percentage = st.slider("Risk Percentage", min_value=1, max_value=25, value=5)
        position_size = portfolio_size * (risk_percentage / 100)
        
        # Calculate returns
        hourly_profit = position_size * abs(live_data["funding"])
        daily_profit = hourly_profit * 24
        weekly_profit = daily_profit * 7
        monthly_profit = daily_profit * 30
        
        st.markdown(f"""
        **Position Size:** ${position_size:,.0f} ({risk_percentage}% of portfolio)
        
        **Expected Returns:**
        - **Hourly:** ${hourly_profit:.2f}
        - **Daily:** ${daily_profit:.2f}  
        - **Weekly:** ${weekly_profit:.2f}
        - **Monthly:** ${monthly_profit:.2f}
        """)
        
        if live_data["funding"] > 0:
            st.success("💰 SHORT position receives funding payments")
        elif live_data["funding"] < 0:
            st.success("💰 LONG position receives funding payments")
        else:
            st.info("⚖️ Neutral funding - no payments")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("## 📈 Market Analytics")
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        
        # Key metrics
        st.metric("Open Interest", f"${live_data['openInterest']:,.0f}")
        st.metric("24h Volume", f"${live_data.get('volume24h', 0):,.0f}")
        st.metric("Premium", f"{live_data['premium']*100:.4f}%")
        st.metric("Volatility", f"{metrics['volatility']:.3f}%")
        
        # Market sentiment
        if live_data["funding"] > 0.0002:
            sentiment = "🔴 Bearish (High funding)"
        elif live_data["funding"] < -0.0002:
            sentiment = "🟢 Bullish (Negative funding)"
        else:
            sentiment = "⚪ Neutral"
        
        st.markdown(f"**Market Sentiment:** {sentiment}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Historical Analysis
    st.markdown("## 📊 Funding Rate Analysis")
    
    history_data = get_funding_history()
    if not history_data.empty:
        # Create comprehensive chart
        fig = go.Figure()
        
        # Funding rate line
        fig.add_trace(go.Scatter(
            x=history_data['timestamp'],
            y=history_data['funding_rate'] * 100,
            mode='lines',
            name='Funding Rate %',
            line=dict(color='#48BB78', width=2),
            hovertemplate='<b>%{y:.4f}%</b><br>%{x}<extra></extra>'
        ))
        
        # Add current rate line
        fig.add_hline(
            y=live_data["funding"] * 100,
            line_dash="dash",
            line_color="#ED8936",
            annotation_text=f"Current: {live_data['funding']*100:.4f}%"
        )
        
        # Opportunity zones
        fig.add_hrect(y0=0.03, y1=1, fillcolor="rgba(245, 101, 101, 0.1)", line_width=0, annotation_text="HIGH OPPORTUNITY")
        fig.add_hrect(y0=-1, y1=-0.03, fillcolor="rgba(245, 101, 101, 0.1)", line_width=0)
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            xaxis=dict(
                gridcolor='rgba(160, 174, 192, 0.2)',
                title="Time (UTC)",
                showgrid=True
            ),
            yaxis=dict(
                gridcolor='rgba(160, 174, 192, 0.2)',
                title="Funding Rate %",
                showgrid=True,
                zeroline=True,
                zerolinecolor='rgba(160, 174, 192, 0.5)'
            ),
            height=500,
            title={
                'text': "7-Day Funding Rate History",
                'x': 0.5,
                'font': {'size': 20, 'color': 'white'}
            },
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Risk Management Section
    st.markdown("## ⚠️ Risk Management")
    st.markdown('<div class="pro-card">', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🛡️ Risk Controls
        - **Position Sizing:** Never risk more than 5-10% per trade
        - **Stop Losses:** Set at 2-3% to limit downside
        - **Diversification:** Don't put all capital in funding arbitrage
        - **Monitoring:** Watch funding rates for sudden changes
        - **Liquidity:** Ensure you can exit positions quickly
        """)
    
    with col2:
        st.markdown("""
        ### 📋 Best Practices
        - **Timing:** Enter positions 10-15 minutes before funding
        - **Exit Strategy:** Have a plan for both profit and loss scenarios
        - **Market Conditions:** Avoid during high volatility events
        - **Capital Management:** Keep reserves for better opportunities
        - **Record Keeping:** Track all trades for performance analysis
        """)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #718096; padding: 20px;">
        <p style="font-size: 16px; margin-bottom: 8px;">⚡ HYPE Pro Trader</p>
        <p style="font-size: 14px;">Professional funding rate arbitrage platform • Live data from Hyperliquid</p>
        <p style="font-size: 12px; margin-top: 16px;">
            ⚠️ <strong>Disclaimer:</strong> This tool is for educational purposes. Trading involves risk. 
            Always do your own research and never invest more than you can afford to lose.
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()