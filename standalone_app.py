#!/usr/bin/env python3
"""
Standalone HYPE Neural Dashboard - No external dependencies
"""

from flask import Flask, jsonify
import os
import json
from datetime import datetime, timezone

app = Flask(__name__)

# Embedded HTML dashboard - no template files needed
DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HYPE Neural Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            background: linear-gradient(135deg, #0a0a0f 0%, #0f0f17 50%, #141420 100%);
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 100vh;
        }
        
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding: 20px 0;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .logo-icon {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #00ff9d, #3742fa);
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            box-shadow: 0 4px 20px rgba(0, 255, 157, 0.3);
        }
        
        .logo-text {
            font-size: 32px;
            font-weight: 900;
            background: linear-gradient(135deg, #00ff9d, #3742fa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .status { 
            display: flex; 
            align-items: center; 
            gap: 10px;
            color: #00ff9d;
            font-weight: 600;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            background: #00ff9d;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .glass-panel {
            background: rgba(20, 20, 32, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            backdrop-filter: blur(20px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
            margin-bottom: 20px;
        }
        
        .glass-panel:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        }
        
        .grid { display: grid; gap: 20px; }
        .grid-2 { grid-template-columns: 2fr 1fr; }
        .grid-4 { grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); }
        
        .prediction-panel { padding: 40px; }
        
        .prediction-title {
            font-size: 28px;
            font-weight: 800;
            margin-bottom: 10px;
        }
        
        .prediction-subtitle {
            color: #a0a0b0;
            margin-bottom: 30px;
            font-size: 16px;
        }
        
        .prediction-value {
            font-size: 48px;
            font-weight: 900;
            margin: 20px 0;
            text-shadow: 0 0 20px currentColor;
        }
        
        .direction-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            border-radius: 20px;
            font-weight: 700;
            margin-bottom: 20px;
        }
        
        .direction-long {
            background: rgba(0, 255, 157, 0.2);
            color: #00ff9d;
            border: 2px solid #00ff9d;
        }
        
        .direction-short {
            background: rgba(255, 71, 87, 0.2);
            color: #ff4757;
            border: 2px solid #ff4757;
        }
        
        .countdown-panel { padding: 30px; text-align: center; }
        
        .countdown-title {
            font-size: 18px;
            color: #a0a0b0;
            margin-bottom: 20px;
        }
        
        .countdown-time {
            font-size: 36px;
            font-weight: 800;
            color: #3742fa;
            font-family: monospace;
        }
        
        .metric-card { padding: 25px; text-align: center; }
        
        .metric-icon {
            font-size: 32px;
            margin-bottom: 15px;
        }
        
        .metric-value {
            font-size: 28px;
            font-weight: 800;
            margin-bottom: 8px;
            font-family: monospace;
        }
        
        .metric-label {
            color: #a0a0b0;
            font-weight: 600;
        }
        
        .btn {
            padding: 12px 24px;
            border-radius: 12px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin: 5px;
            transition: all 0.3s ease;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #00ff9d, #3742fa);
            color: white;
        }
        
        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .btn:hover { transform: translateY(-2px); }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #a0a0b0;
        }
        
        .error {
            background: rgba(255, 71, 87, 0.1);
            border: 1px solid #ff4757;
            color: #ff4757;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }
        
        @media (max-width: 768px) {
            .grid-2 { grid-template-columns: 1fr; }
            .header { flex-direction: column; gap: 20px; }
            .prediction-value { font-size: 32px; }
            .glass-panel div[style*="grid-template-columns"] { grid-template-columns: 1fr !important; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">
                <div class="logo-icon">⚡</div>
                <div class="logo-text">HYPE Neural</div>
            </div>
            <div class="status">
                <div class="status-dot"></div>
                <span id="status-text">LIVE</span>
            </div>
        </div>

        <div id="app">
            <div class="loading">Loading neural dashboard...</div>
        </div>
    </div>

    <script>
        class Dashboard {
            constructor() {
                this.data = null;
                this.loading = true;
                this.error = null;
                this.init();
            }

            async init() {
                await this.fetchData();
                this.render();
                setInterval(() => this.fetchData(), 5000);
                setInterval(() => this.updateCountdown(), 1000);
            }

            async fetchData() {
                try {
                    const response = await fetch('/api/summary');
                    if (!response.ok) throw new Error('API Error');
                    this.data = await response.json();
                    this.error = null;
                } catch (e) {
                    console.warn('API failed, using mock data');
                    this.data = this.getMockData();
                    this.error = 'Using demo data';
                }
                this.loading = false;
                this.render();
            }

            getMockData() {
                return {
                    predictedDirection: {
                        direction: 'positive',
                        prob_positive: 0.73,
                        confidence: 0.73
                    },
                    predictedFundingRate: {
                        pred_next_funding: 0.00012345,
                        n_models: 5
                    },
                    liveFunding: {
                        funding: 0.00008765,
                        premium: 0.00001234
                    },
                    accuracy: {
                        accuracy: 0.68,
                        count: 25
                    },
                    nextFundingTime: Date.now() + 2400000,
                    coin: 'HYPE'
                };
            }

            formatNumber(num, decimals = 6) {
                return num != null ? Number(num).toFixed(decimals) : '—';
            }

            formatPercent(num) {
                return num != null ? (Number(num) * 100).toFixed(1) + '%' : '—';
            }

            getCountdown() {
                if (!this.data?.nextFundingTime) return '--:--:--';
                
                const remaining = Math.max(0, this.data.nextFundingTime - Date.now());
                const hours = String(Math.floor(remaining / 3600000)).padStart(2, '0');
                const minutes = String(Math.floor((remaining % 3600000) / 60000)).padStart(2, '0');
                const seconds = String(Math.floor((remaining % 60000) / 1000)).padStart(2, '0');
                
                return `${hours}:${minutes}:${seconds}`;
            }

            updateCountdown() {
                const countdownEl = document.getElementById('countdown');
                if (countdownEl) {
                    countdownEl.textContent = this.getCountdown();
                }
            }

            render() {
                const app = document.getElementById('app');
                
                if (this.loading) {
                    app.innerHTML = '<div class="loading">Loading neural dashboard...</div>';
                    return;
                }

                const direction = this.data?.predictedDirection?.direction || 'unknown';
                const isPositive = direction === 'positive';
                const isNegative = direction === 'negative';
                
                // Clear explanation of who receives funding
                let fundingText, fundingColor, directionClass, explanation;
                
                if (isPositive) {
                    fundingText = 'SHORTS RECEIVE FUNDING';
                    fundingColor = '#00ff9d';
                    directionClass = 'direction-long';
                    explanation = 'Positive funding rate → Longs pay Shorts';
                } else if (isNegative) {
                    fundingText = 'LONGS RECEIVE FUNDING';
                    fundingColor = '#ff4757';
                    directionClass = 'direction-short';
                    explanation = 'Negative funding rate → Shorts pay Longs';
                } else {
                    fundingText = 'FUNDING DIRECTION UNCLEAR';
                    fundingColor = '#a0a0b0';
                    directionClass = 'direction-short';
                    explanation = 'Unable to predict funding direction';
                }

                app.innerHTML = `
                    ${this.error ? `<div class="error">⚠️ ${this.error}</div>` : ''}
                    
                    <div class="grid grid-2">
                        <div class="glass-panel prediction-panel">
                            <div class="prediction-title">Funding Rate Prediction</div>
                            <div class="prediction-subtitle">Who will receive the next funding payment?</div>
                            
                            <div class="prediction-value" style="color: ${fundingColor}">
                                ${isPositive ? '💰' : isNegative ? '💸' : '⏳'} ${fundingText}
                            </div>
                            
                            <div class="direction-badge ${directionClass}">
                                ${direction.toUpperCase()} RATE • ${this.formatPercent(this.data?.predictedDirection?.prob_positive)} confidence
                            </div>
                            
                            <div style="color: #a0a0b0; font-size: 16px; margin: 15px 0; font-weight: 500;">
                                ${explanation}
                            </div>
                            
                            <div style="margin-top: 20px;">
                                <a href="https://app.hyperliquid.xyz/perps/HYPE" target="_blank" class="btn btn-primary">
                                    🚀 Trade on Hyperliquid
                                </a>
                                <button class="btn btn-secondary" onclick="dashboard.fetchData()">
                                    🔄 Refresh
                                </button>
                            </div>
                        </div>
                        
                        <div class="glass-panel countdown-panel">
                            <div class="countdown-title">⏰ Next Funding In</div>
                            <div class="countdown-time" id="countdown">${this.getCountdown()}</div>
                            <div style="margin-top: 15px; color: #a0a0b0;">
                                Funding occurs every hour
                            </div>
                        </div>
                    </div>
                    
                    <div class="glass-panel" style="padding: 25px; margin-bottom: 20px; background: rgba(20, 20, 32, 0.7);">
                        <h3 style="color: #00ff9d; margin-bottom: 15px; font-size: 18px;">📚 How Funding Works</h3>
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
                    
                    <div class="grid grid-4">
                        <div class="glass-panel metric-card">
                            <div class="metric-icon">🎯</div>
                            <div class="metric-value" style="color: #00ff9d;">
                                ${this.formatNumber(this.data?.predictedFundingRate?.pred_next_funding, 8)}
                            </div>
                            <div class="metric-label">Predicted Rate</div>
                        </div>
                        
                        <div class="glass-panel metric-card">
                            <div class="metric-icon">📊</div>
                            <div class="metric-value" style="color: #3742fa;">
                                ${this.formatNumber(this.data?.liveFunding?.funding, 6)}
                            </div>
                            <div class="metric-label">Current Rate</div>
                        </div>
                        
                        <div class="glass-panel metric-card">
                            <div class="metric-icon">🏆</div>
                            <div class="metric-value" style="color: #a55eea;">
                                ${this.formatPercent(this.data?.accuracy?.accuracy)}
                            </div>
                            <div class="metric-label">Accuracy</div>
                        </div>
                        
                        <div class="glass-panel metric-card">
                            <div class="metric-icon">🧠</div>
                            <div class="metric-value" style="color: #ffa502;">
                                ${this.data?.predictedFundingRate?.n_models || 5}
                            </div>
                            <div class="metric-label">Neural Models</div>
                        </div>
                    </div>
                `;

                // Update status
                document.getElementById('status-text').textContent = this.error ? 'DEMO' : 'LIVE';
            }
        }

        // Initialize dashboard
        const dashboard = new Dashboard();
    </script>
</body>
</html>'''

def get_mock_data():
    """Generate mock data with current timestamp"""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "predictedFundingRate": {
            "pred_next_funding": 0.00012345,
            "pred_std": 0.000001,
            "n_models": 5
        },
        "predictedDirection": {
            "direction": "positive",
            "prob_positive": 0.73,
            "confidence": 0.73,
            "n_models": 5
        },
        "liveFunding": {
            "funding": 0.00008765,
            "premium": 0.00001234,
            "markPx": 32.45,
            "oraclePx": 32.44
        },
        "nextFundingTime": now_ms + 2400000,  # 40 minutes from now
        "lastComparison": {
            "message": "Demo mode - no real predictions yet"
        },
        "accuracy": {
            "count": 25,
            "correct": 17,
            "accuracy": 0.68
        },
        "coin": "HYPE",
        "serverTime": now_ms,
        "fundingIntervalSeconds": 3600
    }

@app.route("/")
def index():
    """Serve the embedded dashboard"""
    return DASHBOARD_HTML

@app.route("/dashboard")
def dashboard():
    """Serve the embedded dashboard"""
    return DASHBOARD_HTML

@app.route("/api/summary")
def api_summary():
    """Main API endpoint - always works"""
    try:
        data = get_mock_data()
        return jsonify(data)
    except Exception as e:
        # Even if there's an error, return basic data
        return jsonify({
            "error": str(e),
            "predictedDirection": {"direction": "unknown", "prob_positive": 0.5},
            "serverTime": int(datetime.now(timezone.utc).timestamp() * 1000)
        })

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "HYPE Neural Dashboard is running"
    })

@app.route("/test")
def test():
    """Test endpoint"""
    return jsonify({
        "message": "✅ Flask app is working perfectly!",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": {
            "dashboard": "/dashboard",
            "api": "/api/summary",
            "health": "/health"
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    print("=" * 60)
    print("🚀 HYPE Neural Dashboard - Standalone Version")
    print("=" * 60)
    print(f"📊 Dashboard: http://localhost:{port}/dashboard")
    print(f"🔧 Test: http://localhost:{port}/test")
    print(f"❤️  Health: http://localhost:{port}/health")
    print(f"📡 API: http://localhost:{port}/api/summary")
    print("=" * 60)
    
    try:
        app.run(host="0.0.0.0", port=port, debug=False)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("Try a different port with: PORT=8001 python standalone_app.py")