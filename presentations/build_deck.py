#!/usr/bin/env python3
"""
Generate today's Market Pulse Overview deck from scorecard_data.json.

Reads live data from the scorecard pipeline, computes derived values
(extension, bull duration, forward-return bucket, etc.), and shells out
to `node build_deck.js` with the live values in env vars.
"""
from __future__ import annotations
import json, os, re, subprocess, sys
from pathlib import Path
from datetime import date

HERE = Path(__file__).parent
REPO = HERE.parent
SCORECARD = REPO / "scorecard_data.json"
OUT_DIR = HERE
OUT_DIR.mkdir(exist_ok=True)

# ── Static reference data (from research_studies/sp500_extension_study.py) ──
# (bucket_name, lo, hi, avg_fwd_return, pct_of_time)
TREND_BUCKETS = [  # ordered high→low to match dashboard
    (">+20%",        20,  999, 16.4, 0.04),
    ("+15 to +20%",  15,   20, 12.6, 1.2),
    ("+10 to +15%",  10,   15, 10.0, 9.2),
    ("+5 to +10%",    5,   10,  9.9, 24.8),
    ("0 to +5%",      0,    5,  7.6, 33.3),
    ("-5 to 0%",     -5,    0,  6.7, 18.9),
    ("-10 to -5%",  -10,   -5,  8.7, 8.0),
    ("-15 to -10%", -15,  -10, 16.4, 2.6),
    ("<-15%",      -999,  -15, 24.7, 1.9),
]

BREADTH_BUCKETS = [  # ordered high→low
    ("Above 90%", 90, 101, 10.7, 0.8),
    ("80-90%",    80,  90, 13.2, 9.3),
    ("70-80%",    70,  80, 13.9, 15.2),
    ("60-70%",    60,  70, 12.6, 22.3),
    ("50-60%",    50,  60,  6.9, 18.9),
    ("40-50%",    40,  50,  6.7, 14.9),
    ("30-40%",    30,  40,  6.2, 8.7),
    ("20-30%",    20,  30,  9.5, 4.7),
    ("10-20%",    10,  20, 22.2, 3.8),
    ("Below 10%",  0,  10, 44.1, 1.4),
]

# Secular bull #3 reference
BULL3_START = date(2016, 1, 1)
BULL3_START_PRICE = 1810.0
CYCLICAL_START_DATE = "October 2022"
CYCLICAL_START_PRICE = 3577.0
MEDIAN_SECULAR_BULL_YRS = 21  # median of Bull #1 (24y) and Bull #2 (18y)


def parse_ma(wins: list, needle: str) -> float | None:
    """Dig a moving-average value out of a healthWins label like
       'Long-Term Trend · S&P 7,126 vs 4-Year MA 5,180'."""
    for w in wins:
        lab = w.get("label", "") if isinstance(w, dict) else str(w)
        m = re.search(needle + r"\s*([\d,\.]+)", lab)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
    return None


def extension_zone(ext: float) -> str:
    if ext < -10: return "Deeply Oversold"
    if ext < 0:   return "Broken Trend"
    if ext < 5:   return "Building"
    if ext < 15:  return "Healthy Uptrend"
    if ext < 20:  return "Strong Uptrend"
    return "Extreme"


def breadth_zone(pct: float) -> str:
    if pct < 20: return "Oversold / Washout"
    if pct < 40: return "Narrow"
    if pct < 60: return "Narrow"
    if pct < 80: return "Healthy"
    return "Strong"


def bucket_for(buckets, value):
    """Return (name, fwd_return, pct_of_time, index_in_reversed_order)."""
    for i, (name, lo, hi, fwd, tim) in enumerate(buckets):
        if lo <= value < hi:
            # Charts render low→high, but list is high→low, so idx in chart = reversed index
            return name, fwd, tim, len(buckets) - 1 - i
    return buckets[-1][0], buckets[-1][3], buckets[-1][4], 0


def main(output_path: str | None = None):
    with open(SCORECARD) as f:
        d = json.load(f)
    m = d["market"]
    prices = d.get("sp500_daily_prices", [])

    sp_price = prices[-1] if prices else 0.0
    ma150 = (sum(prices[-150:]) / 150) if len(prices) >= 150 else None
    extension = ((sp_price / ma150 - 1) * 100) if ma150 else 0.0

    tailwinds = m.get("healthWins", [])
    headwinds = m.get("healthMisses", [])
    ma4yr = parse_ma(tailwinds, "4-Year MA") or 0.0
    ma4_ext = ((sp_price / ma4yr - 1) * 100) if ma4yr else 0.0

    breadth_pct = float(m.get("breadth", {}).get("pctAbove", 50.0))
    trend_status = m.get("trend", {}).get("score", "Positive")

    # Current buckets
    ext_name, ext_fwd, ext_time, ext_idx = bucket_for(TREND_BUCKETS, extension)
    br_name, br_fwd, br_time, br_idx = bucket_for(BREADTH_BUCKETS, breadth_pct)

    today = date.today()
    bull3_years = (today - BULL3_START).days / 365.25
    bull3_gain = (sp_price / BULL3_START_PRICE - 1) * 100
    cyclical_gain = (sp_price / CYCLICAL_START_PRICE - 1) * 100
    room_to_run_yrs = max(0, round(MEDIAN_SECULAR_BULL_YRS - bull3_years))

    # Text for tailwind/headwind summary lines (4 grouped categories)
    # Extract individual readings we care about
    def grab(wins, label_contains):
        for w in wins:
            lab = w.get("label", "") if isinstance(w, dict) else ""
            if label_contains in lab:
                m2 = re.search(r"Now:\s*([^\s·]+)", lab)
                return m2.group(1) if m2 else ""
        return ""

    # Parse every indicator into {name, value, threshold} so the deck can
    # render them as tidy rows with the "what flips them" call-out inline.
    def parse_indicator(lab: str) -> dict:
        match = re.match(
            r"(?P<name>[^·]+)·\s*Now:\s*(?P<val>[^·]+)·\s*Healthy:\s*(?P<threshold>.+)",
            lab,
        )
        if match:
            name = match.group("name").strip()
            val = match.group("val").strip()
            thr = match.group("threshold").strip().split("—")[0].strip()
            return {"name": name, "value": val, "threshold": thr}
        # Trend labels have a different shape: "Long-Term Trend · S&P 7,126 vs 4-Year MA 5,180"
        if "·" in lab:
            head, rest = lab.split("·", 1)
            return {"name": head.strip(), "value": rest.strip(), "threshold": ""}
        return {"name": lab, "value": "", "threshold": ""}

    tailwind_items = [parse_indicator(w.get("label", "")) for w in tailwinds]
    headwind_items = [parse_indicator(w.get("label", "")) for w in headwinds]

    # Condensed 4-line thematic summary for slide 2's right column (fits the box cleanly).
    def grab(wins, label_contains):
        for w in wins:
            lab = w.get("label", "") if isinstance(w, dict) else ""
            if label_contains in lab:
                m2 = re.search(r"Now:\s*([^\s·]+)", lab)
                return m2.group(1) if m2 else ""
        return ""

    labor = grab(tailwinds, "Labor Market")
    gdp_t = grab(tailwinds, "GDP Growth")
    infl_t= grab(tailwinds, "Inflation")
    vix_t = grab(tailwinds, "Volatility")
    hy_t  = grab(tailwinds, "Credit Spreads")
    move_t= grab(tailwinds, "MOVE Index")
    yc_t  = grab(tailwinds, "Yield Curve")
    cf_t  = grab(tailwinds, "Economic Activity")
    oil_t = grab(tailwinds, "Oil Price")
    dxy_t = grab(tailwinds, "US Dollar")
    jc_t  = grab(tailwinds, "Jobless Claims")
    rr_t  = grab(tailwinds, "Real Interest Rate")
    pc_t  = grab(tailwinds, "Sentiment")
    aaii_t= grab(tailwinds, "AAII Bull Sentiment")
    ipo_t = grab(tailwinds, "IPO ETF")

    # Build 4 thematic lines, only including items that are CURRENT tailwinds
    def join_theme(parts):
        """Drop empty pieces and join with ' · '."""
        clean = [p for p in parts if p]
        return " · ".join(clean)

    tailwind_lines = [
        join_theme([
            f"Labor {labor}" if labor else "",
            f"GDP {gdp_t}" if gdp_t else "",
            f"Inflation {infl_t}" if infl_t else "",
            f"CFNAI {cf_t}" if cf_t else "",
        ]),
        "Trend positive (above 150-day + 4-year MA)" if trend_status == "Positive" else "",
        join_theme([
            f"VIX {vix_t}" if vix_t else "",
            f"HY OAS {hy_t}" if hy_t else "",
            f"MOVE {move_t}" if move_t else "",
            f"Real rate {rr_t}" if rr_t else "",
        ]),
        join_theme([
            f"Yield curve {yc_t}" if yc_t else "",
            f"P/C {pc_t}" if pc_t else "",
            f"AAII {aaii_t}" if aaii_t else "",
            "IPO ETF risk-on" if ipo_t else "",
        ]),
    ]
    # Drop any empty theme lines
    tailwind_lines = [t for t in tailwind_lines if t]

    headwind_lines = [
        f"{h['name']} {h['value']} (want {h['threshold']})".strip() if h['threshold']
        else f"{h['name']} {h['value']}".strip()
        for h in headwind_items
    ]

    # Format output filename with today's date
    if not output_path:
        output_path = str(OUT_DIR / f"Market_Pulse_Overview_{today.isoformat()}.pptx")

    # Build env for node
    env = dict(os.environ)
    env.update({
        "DECK_DATE":         today.strftime("%B %-d, %Y"),
        "DECK_SP":           f"{sp_price:,.0f}",
        "DECK_HEALTH":       str(m.get("healthScore", "")),
        "DECK_LABEL":        m.get("healthLabel", "Cautiously Bullish"),
        "DECK_VIEW":         m.get("healthLabel", "Bullish").split()[-1],  # "Bullish" from "Cautiously Bullish"
        "DECK_TW_COUNT":     str(len(tailwinds)),
        "DECK_HW_COUNT":     str(len(headwinds)),
        "DECK_TW_LINES":     json.dumps(tailwind_lines),
        "DECK_HW_LINES":     json.dumps(headwind_lines),
        "DECK_TW_ITEMS":     json.dumps(tailwind_items),
        "DECK_HW_ITEMS":     json.dumps(headwind_items),
        "DECK_TREND":        trend_status,
        "DECK_MA150":        f"{ma150:,.0f}" if ma150 else "—",
        "DECK_MA4YR":        f"{ma4yr:,.0f}" if ma4yr else "—",
        "DECK_MA150_PCT":    f"{extension:+.1f}%",
        "DECK_MA4YR_PCT":    f"{ma4_ext:+.1f}%",
        "DECK_CYC_GAIN":     f"{cyclical_gain:.0f}",
        "DECK_EXT":          f"{extension:+.1f}%",
        "DECK_EXT_ZONE":     extension_zone(extension),
        "DECK_EXT_TIME":     f"{ext_time:.1f}%",
        "DECK_EXT_FWD":      f"+{ext_fwd:.1f}%",
        "DECK_EXT_IDX":      str(ext_idx),
        "DECK_BREADTH":      f"{breadth_pct:.0f}",
        "DECK_BR_ZONE":      breadth_zone(breadth_pct),
        "DECK_BR_FWD":       f"+{br_fwd:.0f}%",
        "DECK_BR_IDX":       str(br_idx),
        "DECK_BULL3_YRS":    f"~{bull3_years:.0f} yrs so far",
        "DECK_BULL3_GAIN":   f"+{bull3_gain:.0f}% so far",
        "DECK_ROOM_TO_RUN":  f"~{room_to_run_yrs} years",
        "DECK_PB_TOTAL":     str(d.get("pullbackStats", {}).get("total", 62)),
        "DECK_OUTPUT":       output_path,
    })

    # Shell out to node
    os.chdir(HERE)
    print(f"Generating deck with live data (as of {today.isoformat()})...")
    print(f"  S&P 500: {sp_price:,.0f}  ·  Health: {m.get('healthScore')}/100 {m.get('healthLabel')}")
    print(f"  Extension: {extension:+.2f}% ({extension_zone(extension)})  ·  Breadth: {breadth_pct:.0f}% ({breadth_zone(breadth_pct)})")
    print(f"  Bull #3: {bull3_years:.1f} yrs, +{bull3_gain:.0f}%  ·  Room to run: ~{room_to_run_yrs}y")

    result = subprocess.run(["node", "build_deck.js"], env=env)
    if result.returncode == 0:
        print(f"\n✅ Deck written to: {output_path}")
    else:
        print("\n❌ Node failed with exit code", result.returncode)
        sys.exit(result.returncode)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(arg)
