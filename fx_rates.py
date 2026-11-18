"""
Live currency exchange rates.

Fetches real rates from a free, no-key-required public API so that
switching display currency actually converts amounts to their real-world
value, not just relabels the symbol. Results are cached in memory for a
few hours to avoid hammering the API and to keep the app responsive.

If the live fetch fails (no internet, API down, etc.) the service falls
back to a static table of approximate rates captured on the date noted
below -- clearly marked as "fallback" in the response so the frontend can
tell the user their rates might be stale.
"""
from __future__ import annotations
import json
import time
import urllib.request
import urllib.error
import datetime as dt
from typing import Optional, Dict, List

SUPPORTED_CURRENCIES = ["INR", "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "SGD", "AED"]

# Approximate real-world rates captured 26 Aug 2026 (1 INR = X target
# currency), used only when a live fetch isn't possible. Sourced from
# publicly available mid-market rate aggregators at that date.
FALLBACK_RATES: Dict[str, float] = {
    "INR": 1.0,
    "USD": 0.010494,
    "EUR": 0.008997,
    "GBP": 0.007701,
    "JPY": 1.6694,
    "AUD": 0.014622,
    "CAD": 0.014547,
    "SGD": 0.013330,
    "AED": 0.038536,
}
FALLBACK_DATE = "2026-08-26"

CACHE_TTL_SECONDS = 6 * 3600  # refetch at most every 6 hours
_cache = {"rates": None, "source": None, "fetched_at": None, "fetched_at_epoch": 0.0}


def _fetch_live(base: str = "INR") -> Dict[str, float]:
    """Calls a free, keyless FX-rate API. Raises on any failure so the
    caller can fall back cleanly."""
    url = f"https://open.er-api.com/v6/latest/{base}"
    req = urllib.request.Request(url, headers={"User-Agent": "SpendSense-XAI/1.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
    if data.get("result") != "success" or "rates" not in data:
        raise ValueError("FX API did not return a successful result")
    return data["rates"]


def get_rates(supported: Optional[List[str]] = None) -> dict:
    """Returns rates for all supported currencies relative to 1 INR,
    e.g. {"INR": 1.0, "USD": 0.0105, ...}. Cached for CACHE_TTL_SECONDS."""
    supported = supported or SUPPORTED_CURRENCIES
    now = time.time()

    if _cache["rates"] is not None and (now - _cache["fetched_at_epoch"]) < CACHE_TTL_SECONDS:
        return _response(_cache["rates"], _cache["source"], _cache["fetched_at"])

    try:
        live = _fetch_live("INR")
        rates = {c: live[c] for c in supported if c in live}
        rates["INR"] = 1.0
        for c in supported:
            rates.setdefault(c, FALLBACK_RATES.get(c, 1.0))
        source = "live"
    except Exception:
        rates = {c: FALLBACK_RATES.get(c, 1.0) for c in supported}
        source = "fallback"

    fetched_at = dt.datetime.utcnow().isoformat() + "Z"
    _cache.update({"rates": rates, "source": source, "fetched_at": fetched_at, "fetched_at_epoch": now})
    return _response(rates, source, fetched_at)


def _response(rates: dict, source: str, fetched_at: str) -> dict:
    return {
        "base": "INR",
        "rates": rates,
        "source": source,
        "fetched_at": fetched_at,
        "fallback_dated": FALLBACK_DATE if source == "fallback" else None,
    }
