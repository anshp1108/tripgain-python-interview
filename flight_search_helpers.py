"""Helper utilities for flight search scraping.

Contains small, focused functions so the main scraper file stays compact.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, Optional


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(node) -> str:
    try:
        return node.inner_text().strip()
    except Exception:
        return ""


def _extract_from_text_block(text: str) -> Dict[str, Optional[str]]:
    # heuristics: find times, price, flight-number-like patterns, airline names
    res = {"airline": None, "flight_number": None, "departure": None, "arrival": None, "price": None}

    if not text:
        return res

    # times like 06:30 or 6:30
    times = re.findall(r"\d{1,2}:\d{2}", text)
    if len(times) >= 2:
        res["departure"] = times[0]
        res["arrival"] = times[1]
    elif len(times) == 1:
        res["departure"] = times[0]

    # price (₹ or Rs or INR)
    price_match = re.search(r"(₹\s?\d{1,3}(?:[\,\d]{0,})|Rs\.?\s?\d[\d,]*)", text)
    if price_match:
        res["price"] = price_match.group(1)

    # flight number like AI-504 or 6E123
    fn_match = re.search(r"\b([A-Z]{2,3}[- ]?\d{1,4}|\d[A-Z]?[- ]?\d{1,4})\b", text)
    if fn_match:
        res["flight_number"] = fn_match.group(1).replace(" ", "").replace("-", "-")

    # airline: look for capitalized words from a short known list first
    airlines = [
        "IndiGo",
        "Air India",
        "SpiceJet",
        "Vistara",
        "GoAir",
        "Alliance Air",
        "AirAsia",
        "Air India Express",
        "Trujet",
        "Akasa Air",
    ]
    for a in airlines:
        if a.lower() in text.lower():
            res["airline"] = a
            break

    # fallback: first line of text (often airline name)
    if res["airline"] is None:
        first_line = text.splitlines()[0].strip() if text else None
        if first_line and len(first_line) < 40:
            res["airline"] = first_line

    return res
