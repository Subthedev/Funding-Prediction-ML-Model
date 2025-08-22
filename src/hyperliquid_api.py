import time
import logging
from typing import Dict, List, Optional, Any
import requests

from .config import HL_INFO_URL


logger = logging.getLogger(__name__)


def _post_info(body: Dict[str, Any], timeout: int = 20) -> Any:
    headers = {"Content-Type": "application/json"}
    response = requests.post(HL_INFO_URL, json=body, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_meta_and_asset_ctxs() -> Any:
    return _post_info({"type": "metaAndAssetCtxs"})


def get_meta() -> Any:
    return _post_info({"type": "meta"})


def coin_in_universe(coin: str) -> bool:
    try:
        meta = get_meta()
    except Exception:
        logger.exception("Failed to fetch meta")
        return False
    universe = meta.get("universe", [])
    return any(entry.get("name") == coin for entry in universe)


def fetch_funding_history(
    coin: str,
    start_time_ms: int,
    end_time_ms: Optional[int] = None,
    max_pages: int = 1000,
) -> List[Dict[str, Any]]:
    """
    Paginates funding history (cap ~500 per response). Use last timestamp+1 as next start.
    """
    results: List[Dict[str, Any]] = []
    current_start = start_time_ms
    effective_end = end_time_ms
    for _ in range(max_pages):
        body = {"type": "fundingHistory", "coin": coin, "startTime": int(current_start)}
        if effective_end is not None:
            body["endTime"] = int(effective_end)
        page = _post_info(body)
        if not page:
            break
        # Ensure sorted by time
        page_sorted = sorted(page, key=lambda x: x.get("time", 0))
        results.extend(page_sorted)
        last_time = page_sorted[-1].get("time", current_start)
        # Stop if we did not progress
        if last_time <= current_start:
            break
        # Pagination: next start is last_time + 1
        current_start = int(last_time) + 1
        # If end boundary reached
        if effective_end is not None and current_start > effective_end:
            break
        # Be polite
        time.sleep(0.05)
    return results


def fetch_predicted_fundings() -> Any:
    return _post_info({"type": "predictedFundings"})


def get_predicted_funding_for_coin(coin: str, venue: str = "HlPerp") -> Optional[Dict[str, Any]]:
    """Return predicted funding payload for a coin at a given venue, if available."""
    try:
        data = fetch_predicted_fundings()
        for entry in data:
            if not isinstance(entry, list) or len(entry) != 2:
                continue
            c, venues = entry
            if c == coin:
                for v in venues:
                    if isinstance(v, list) and len(v) == 2 and v[0] == venue:
                        return v[1]
    except Exception:
        logger.exception("Failed to fetch predicted fundings")
    return None


def get_current_funding_for_coin(coin: str) -> Optional[Dict[str, Any]]:
    """
    Return current funding context for the coin using metaAndAssetCtxs.
    Example keys in result: funding, premium, markPx, oraclePx, openInterest.
    """
    try:
        meta, ctxs = get_meta_and_asset_ctxs()
        universe = meta.get("universe", [])
        for idx, u in enumerate(universe):
            if u.get("name") == coin:
                if idx < len(ctxs):
                    ctx = ctxs[idx]
                    # Normalize numeric fields to floats when possible
                    out: Dict[str, Any] = {}
                    for k in ["funding", "premium", "markPx", "oraclePx", "openInterest"]:
                        v = ctx.get(k)
                        if v is None:
                            continue
                        try:
                            out[k] = float(v)
                        except Exception:
                            out[k] = v
                    return out
                break
    except Exception:
        logger.exception("Failed to fetch current funding context")
    return None


def fetch_candles(
    coin: str,
    interval: str,
    start_time_ms: int,
    end_time_ms: Optional[int] = None,
) -> List[Dict[str, Any]]:
    body: Dict[str, Any] = {
        "type": "candleSnapshot",
        "req": {"coin": coin, "interval": interval, "startTime": int(start_time_ms)},
    }
    if end_time_ms is not None:
        body["req"]["endTime"] = int(end_time_ms)
    data = _post_info(body)
    # Normalize fields we use: t (open time), T (close time), c (close), o (open), h (high), l (low), v (volume)
    return data or [] 