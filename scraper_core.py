"""Core scraper implementation for budgetticket.in.

This file holds the heavy Playwright-based `scrape_flights` implementation. It imports
small helpers from `flight_search_helpers.py` so the public wrapper file stays compact.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Dict

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from flight_search_helpers import _iso_utc_now, _safe_text, _extract_from_text_block


def scrape_flights(
    origin: str,
    destination: str,
    journey_date: str,
    *,
    headless: bool = True,
    save_path: str = "flight_results.json",
    fast_mode: bool = True,
) -> List[Dict]:
    """Scrape flights from budgetticket.in using Playwright.

    origin, destination: city names (e.g., "Bangalore", "Delhi")
    journey_date: YYYY-MM-DD (a valid future date)
    Returns: list of flight dicts and writes JSON to save_path.
    """

    results: List[Dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        # timeouts
        if fast_mode:
            page.set_default_navigation_timeout(15000)
            page.set_default_timeout(6000)
        else:
            page.set_default_navigation_timeout(20000)
            page.set_default_timeout(10000)

        # Per user request: do not block any resources. Allow full page load so dynamic
        # content and third-party scripts can run; this may increase runtime but
        # ensures completeness of extracted data.
        def _route_handler(route, request):
            try:
                return route.continue_()
            except Exception:
                try:
                    return route.continue_()
                except Exception:
                    pass

        try:
            page.route("**/*", _route_handler)
        except Exception:
            pass

        goto_timeout = 40000 if fast_mode else 60000
        page.goto("https://www.budgetticket.in", timeout=goto_timeout)

        # Try to click Flights tab or navigate directly
        try:
            page.click('a[href*="flight"]', timeout=3000)
        except Exception:
            pass

        origin_selectors = [
            'input[id*="origin"]',
            'input[name*="origin"]',
            'input[placeholder*="From"]',
            'input[aria-label*="From"]',
            'input[placeholder*="From city"]',
        ]

        dest_selectors = [
            'input[id*="destination"]',
            'input[name*="destination"]',
            'input[placeholder*="To"]',
            'input[aria-label*="To"]',
            'input[placeholder*="To city"]',
        ]

        def _fill_autocomplete(sel_list, value):
            for s in sel_list:
                try:
                    if page.query_selector(s):
                        page.fill(s, value)
                        page.wait_for_timeout(800)
                        page.keyboard.press("Enter")
                        return True
                except Exception:
                    continue
            return False

        _fill_autocomplete(origin_selectors, origin)
        _fill_autocomplete(dest_selectors, destination)

        date_selectors = [
            'input[type="date"]',
            'input[placeholder*="Depart"]',
            'input[placeholder*="Journey"]',
            'input[aria-label*="Depart"]',
        ]
        date_filled = False
        for ds in date_selectors:
            try:
                node = page.query_selector(ds)
                if node:
                    try:
                        page.click(ds)
                    except Exception:
                        pass

                    def _pick_date_ui(page, target_date: str) -> bool:
                        try:
                            selector = f'[data-date="{target_date}"]'
                            el = page.query_selector(selector)
                            if el:
                                el.click()
                                return True
                        except Exception:
                            pass

                        try:
                            day = str(int(target_date.split("-")[2]))
                            year = target_date.split("-")[0]
                            script = """(targetDay, targetYear) => {
  const nodes = Array.from(document.querySelectorAll('td, button, a, div'));
  for (const n of nodes) {
    if (!n.textContent) continue;
    if (n.textContent.trim() === String(targetDay)) {
      let p = n.parentElement;
      while (p) {
        if (p.textContent && p.textContent.includes(targetYear)) { n.click(); return true; }
        p = p.parentElement;
      }
    }
  }
  return false;
}"""
                            clicked = page.evaluate(script, day, year)
                            if clicked:
                                return True
                        except Exception:
                            pass

                        try:
                            page.fill(ds, target_date)
                            page.wait_for_timeout(200)
                            page.keyboard.press("Enter")
                            return True
                        except Exception:
                            return False

                    if _pick_date_ui(page, journey_date):
                        date_filled = True
                        break
            except Exception:
                continue

        if not date_filled:
            try:
                page.evaluate("(d) => { const i = document.querySelector('input[type=date]'); if(i){ i.value = d; i.dispatchEvent(new Event('input')); } }", journey_date)
            except Exception:
                try:
                    page.fill('input', journey_date)
                except Exception:
                    pass

        search_selectors = [
            'button:has-text("Search")',
            'button:has-text("Search Flights")',
            'button[type="submit"]',
            'a:has-text("Search")',
        ]

        clicked = False
        for ss in search_selectors:
            try:
                if page.query_selector(ss):
                    page.click(ss)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            page.keyboard.press("Enter")

        result_selectors = [
            '[data-test="flight-card"]',
            '.flight-card',
            '.result',
            '.search-results',
            '.listing',
            '.search-list',
        ]

        found = False
        for rs in result_selectors:
            try:
                page.wait_for_selector(rs, timeout=8000)
                found = True
                break
            except PlaywrightTimeoutError:
                continue

        if not found:
            page.wait_for_timeout(1200)

        def _clear_price_filters(page):
            tried = []
            selectors = [
                "button:has-text('Clear')",
                "button:has-text('Clear filters')",
                "button[aria-label*='Clear']",
                "button:has-text('Show all')",
                "button:has-text('All')",
                "a:has-text('Show all')",
                ".filter-clear",
                ".clear-filters",
                ".filter-reset",
            ]
            for s in selectors:
                try:
                    el = page.query_selector(s)
                    if el:
                        el.click()
                        tried.append(s)
                except Exception:
                    continue

            try:
                sort_selectors = ["select[name*='sort']", "select.sort", "select[id*='sort']"]
                for ss in sort_selectors:
                    sel = page.query_selector(ss)
                    if sel:
                        options = page.eval_on_selector_all(ss, "els => els.map(e => e.value)")
                        if options and len(options) > 0:
                            page.select_option(ss, options[0])
            except Exception:
                pass

            return tried

        cleared = _clear_price_filters(page)
        if cleared:
            page.wait_for_timeout(1200)

        card_selectors = [
            '.flight-card',
            '[data-test="flight-card"]',
            '.result',
            '.listing .item',
            '.search-list .item',
            '.srpCard',
            'article',
            '.flightRow',
        ]

        # Fast-path: use a single page.evaluate to collect text blobs for candidate nodes
        if fast_mode:
            try:
                js_collect = """
                (selectors) => {
                  const seen = new Set();
                  const out = [];
                  for (const sel of selectors) {
                    try {
                      const nodes = Array.from(document.querySelectorAll(sel));
                      for (const n of nodes) {
                        const txt = (n.innerText || '').trim();
                        if (!txt) continue;
                        const sig = txt.slice(0,200);
                        if (seen.has(sig)) continue;
                        seen.add(sig);
                        const priceEl = n.querySelector('.price, .fare, [data-price], .amount');
                        const img = n.querySelector('img');
                        const airlineText = img ? (img.alt || '') : '';
                        const priceText = priceEl ? (priceEl.innerText || '') : '';
                        out.push({ text: txt, airlineHint: airlineText, priceHint: priceText });
                      }
                    } catch (e) { continue; }
                  }
                  return out;
                }
                """
                blobs = page.evaluate(js_collect, card_selectors)
            except Exception:
                blobs = []

            for b in blobs:
                try:
                    text = b.get('text', '') if isinstance(b, dict) else (b or '')
                    airline_hint = b.get('airlineHint', '') if isinstance(b, dict) else ''
                    price_hint = b.get('priceHint', '') if isinstance(b, dict) else ''
                    extracted = _extract_from_text_block(text)
                    if not extracted.get('airline') and airline_hint:
                        extracted['airline'] = airline_hint
                    if not extracted.get('price') and price_hint:
                        extracted['price'] = price_hint

                    flight = {
                        'airline': extracted.get('airline') or '',
                        'flight_number': extracted.get('flight_number') or '',
                        'departure': extracted.get('departure') or '',
                        'arrival': extracted.get('arrival') or '',
                        'price': extracted.get('price') or '',
                        'origin': origin,
                        'destination': destination,
                        'searchdatetime': _iso_utc_now(),
                    }
                    results.append(flight)
                except Exception:
                    continue

        else:
            candidates = []
            for cs in card_selectors:
                try:
                    nodes = page.query_selector_all(cs)
                    if nodes:
                        candidates.extend(nodes)
                except Exception:
                    continue

            seen = set()
            for node in candidates:
                try:
                    text = _safe_text(node)
                    if not text:
                        continue
                    sig = text[:200]
                    if sig in seen:
                        continue
                    seen.add(sig)

                    extracted = _extract_from_text_block(text)
                    if not extracted.get("price"):
                        price_node = node.query_selector("text=₹, text=Rs, .price, .fare")
                        if price_node:
                            extracted["price"] = _safe_text(price_node)

                    if not extracted.get("airline"):
                        img = node.query_selector("img")
                        if img:
                            alt = img.get_attribute("alt")
                            if alt:
                                extracted["airline"] = alt.strip()

                    flight = {
                        "airline": extracted.get("airline") or "",
                        "flight_number": extracted.get("flight_number") or "",
                        "departure": extracted.get("departure") or "",
                        "arrival": extracted.get("arrival") or "",
                        "price": extracted.get("price") or "",
                        "origin": origin,
                        "destination": destination,
                        "searchdatetime": _iso_utc_now(),
                    }
                    results.append(flight)
                except Exception:
                    continue

        if not results:
            body_text = page.content()
            payload = _extract_from_text_block(body_text)
            results.append({
                "airline": payload.get("airline") or "",
                "flight_number": payload.get("flight_number") or "",
                "departure": payload.get("departure") or "",
                "arrival": payload.get("arrival") or "",
                "price": payload.get("price") or "",
                "origin": origin,
                "destination": destination,
                "searchdatetime": _iso_utc_now(),
            })

        browser.close()

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Total Flights Extracted: {len(results)}")
    return results
