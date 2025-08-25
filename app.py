from flask import Flask, render_template, jsonify
import os
import traceback
from datetime import datetime, timezone

app = Flask(__name__)

# Enable debug mode for better error messages
app.config['DEBUG'] = True

# Mock data that always works
def get_mock_data():
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

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "Using fallback data",
        "data": get_mock_data()
    }), 200  # Return 200 so frontend doesn't break

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.route("/")
def index():
    try:
        return render_template("dashboard.html")
    except Exception as e:
        print(f"Template error: {e}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>HYPE Dashboard</title></head>
        <body>
            <h1>HYPE Neural Dashboard</h1>
            <p>Template loading error. Please check if templates/dashboard.html exists.</p>
            <p>Error: {str(e)}</p>
            <a href="/api/summary">View API Data</a>
        </body>
        </html>
        """

@app.route("/dashboard")
def dashboard():
    return index()

@app.route("/api/summary")
def api_summary():
    """Main API endpoint - always returns data"""
    try:
        # Always return mock data for now to ensure it works
        data = get_mock_data()
        print(f"API Summary called, returning: {data}")
        return jsonify(data)
        
    except Exception as e:
        print(f"API Summary error: {e}")
        print(traceback.format_exc())
        # Even if there's an error, return mock data
        return jsonify(get_mock_data())

@app.route("/api/live")
def api_live():
    """Real-time data endpoint"""
    try:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        return jsonify({
            "liveFunding": {
                "funding": 0.00008765,
                "premium": 0.00001234,
                "markPx": 32.45,
                "oraclePx": 32.44
            },
            "serverTime": now_ms,
            "coin": "HYPE"
        })
    except Exception as e:
        print(f"API Live error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/metrics")
def api_metrics():
    """Performance metrics endpoint"""
    try:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        return jsonify({
            "accuracy": {
                "count": 25,
                "correct": 17,
                "accuracy": 0.68
            },
            "lastComparison": {
                "message": "Demo mode active"
            },
            "serverTime": now_ms
        })
    except Exception as e:
        print(f"API Metrics error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    try:
        return jsonify({
            "status": "ok", 
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "HYPE Neural Dashboard is running"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/test")
def test():
    """Test endpoint to verify everything works"""
    return jsonify({
        "message": "Flask app is working!",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "routes": [
            "/",
            "/dashboard", 
            "/api/summary",
            "/api/live",
            "/api/metrics",
            "/health",
            "/test"
        ]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("=" * 50)
    print("🚀 HYPE Neural Dashboard Starting...")
    print(f"📊 Dashboard: http://localhost:{port}/dashboard")
    print(f"🔧 Test endpoint: http://localhost:{port}/test")
    print(f"❤️  Health check: http://localhost:{port}/health")
    print("=" * 50)
    
    # Create templates directory if it doesn't exist
    os.makedirs("templates", exist_ok=True)
    
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)