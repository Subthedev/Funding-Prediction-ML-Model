import json
from datetime import datetime, timezone


from .config import DEFAULT_COIN, DEFAULT_INTERVAL
from .hyperliquid_api import get_predicted_funding_for_coin, get_current_funding_for_coin
import subprocess
import sys


PYTHON = sys.executable


def run_cmd(args):
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return proc.stdout


def once(coin: str = DEFAULT_COIN, interval: str = DEFAULT_INTERVAL):
    # Fetch latest data window (uses default days from fetch_data)
    run_cmd([PYTHON, "-m", "src.fetch_data", "--coin", coin, "--interval", interval])
    # Train cls (could be scheduled less frequently; here for simplicity)
    run_cmd([PYTHON, "-m", "src.train_cls"])
    # Infer
    out = run_cmd([PYTHON, "-m", "src.infer_cls"])
    infer = json.loads(out)

    # HL predicted and current funding
    hl_pred = get_predicted_funding_for_coin(coin)
    hl_current = get_current_funding_for_coin(coin)

    payload = {
        "time": datetime.now(timezone.utc).isoformat(),
        "coin": coin,
        "direction": infer.get("direction"),
        "prob_positive": infer.get("prob_positive"),
        "confidence": infer.get("conf"),
        "n_models": infer.get("n_models"),
        "hl_predicted_funding": hl_pred,  # includes fundingRate and nextFundingTime
        "hl_current_ctx": hl_current,      # includes current funding and premium
    }
    print(json.dumps(payload, indent=2))


def main():
    # Run once. For continuous hourly loop, you can uncomment below.
    once()
    # while True:
    #     now = now_ms()
    #     # Sleep until next hour boundary
    #     sleep_sec = 3600 - (now // 1000) % 3600
    #     time.sleep(sleep_sec + 1)
    #     once()


if __name__ == "__main__":
    main() 