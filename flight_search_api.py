"""FastAPI wrapper that exposes a /flight-search endpoint.

Example:
  uvicorn flight_search_api:app --reload --host 127.0.0.1 --port 8000
  GET /flight-search?origin=Bangalore&destination=Delhi&journey_date=2025-10-18

Note: Running the endpoint requires Playwright and its browsers to be installed.
"""

from __future__ import annotations

import asyncio
from typing import List
from datetime import datetime, timezone

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse

from flight_search_automation import scrape_flights

app = FastAPI(title="Flight Search Scraper API")


def _run_scraper_sync(origin: str, destination: str, journey_date: str) -> List[dict]:
    # runs the blocking sync scraper and returns results
    return scrape_flights(origin, destination, journey_date, headless=True, save_path="flight_results.json")


@app.get("/flight-search")
async def flight_search(
    origin: str = Query(..., description="Origin city"),
    destination: str = Query(..., description="Destination city"),
    journey_date: str = Query(..., description="Journey date in YYYY-MM-DD"),
):
    """Endpoint that triggers Playwright scraping and returns JSON results.

    Because Playwright is blocking (sync) in our helper, run it in a thread via loop.run_in_executor.
    """
    loop = asyncio.get_running_loop()
    try:
        results = await loop.run_in_executor(None, _run_scraper_sync, origin, destination, journey_date)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Ensure required fields are present on every result: origin, destination, searchdatetime
    now_iso = datetime.now(timezone.utc).isoformat()
    for r in results:
        try:
            if not r.get("origin"):
                r["origin"] = origin
            if not r.get("destination"):
                r["destination"] = destination
            # Always set/override searchdatetime to the API call time for clarity
            r["searchdatetime"] = now_iso
        except Exception:
            # best-effort: skip malformed items
            continue

    return JSONResponse(content=results)
