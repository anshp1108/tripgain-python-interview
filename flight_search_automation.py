"""Thin wrapper that exposes a compact public API.

This file intentionally keeps only a tiny surface area so it's easy to read
and maintain. The heavy implementation lives in `scraper_core.py` and small
helpers in `flight_search_helpers.py`.
"""

from __future__ import annotations

from typing import List, Dict

from scraper_core import scrape_flights


if __name__ == "__main__":
    # Example CLI: keep this file short — it only forwards to scraper_core
    import sys
    from datetime import datetime, timedelta

    origin = "Bangalore"
    destination = "Delhi"
    tomorrow = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    journey_date = tomorrow

    if len(sys.argv) >= 4:
        origin = sys.argv[1]
        destination = sys.argv[2]
        journey_date = sys.argv[3]

    scrape_flights(origin, destination, journey_date, headless=True, save_path="flight_results.json")
