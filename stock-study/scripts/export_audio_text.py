#!/usr/bin/env python3
"""
export_audio_text.py — Export study content as plain text for NotebookLM,
TTS services, or any other tool that wants narrative source material.

Produces:
    audio_source/focused-large-cap.txt
    audio_source/large-cap.txt
    audio_source/mid-cap.txt
    audio_source/small-cap.txt
    audio_source/micro-cap.txt
    audio_source/all-funds-overview.txt       (universe view)
    audio_source/all-funds-district-only.txt  (just district intros, no companies)

Each fund file contains:
  - Fund intro (tagline + story paragraphs)
  - Every visible act/district in order with their intros
  - Every company narrative (big picture + story + sound bite)

Upload one of these to https://notebooklm.google.com, click "Audio Overview",
and you get a ~15-minute podcast-style episode you can download as an MP3.
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "audio_source"

FUNDS = [
    ("focused-large-cap", "Focused Large Cap"),
    ("large-cap", "Large Cap"),
    ("mid-cap", "Mid Cap"),
    ("small-cap", "Small Cap"),
    ("micro-cap", "Micro Cap"),
]


def load_study():
    with (DATA / "study.json").open() as f:
        return json.load(f)


def load_holdings(fund_slug):
    path = DATA / "holdings" / f"{fund_slug}.csv"
    with path.open() as f:
        return [r["ticker"].strip() for r in csv.DictReader(f) if r["ticker"].strip() and r["ticker"].strip() != "$CASH"]


def smart_para(paragraph: str) -> str:
    """Clean up a paragraph for TTS: strip markdown artifacts, normalize dashes."""
    s = paragraph.strip()
    # Em-dashes and en-dashes sound natural in TTS; leave them alone
    # But strip stray markdown, double spaces, etc.
    s = re.sub(r"\s+", " ", s)
    return s


def render_company(ticker: str, entry: dict) -> str:
    """One company narrative block. Avoids ticker-only lines that sound awkward spoken."""
    name = entry.get("name", "")
    big = smart_para(entry.get("big_picture", ""))
    story = smart_para(entry.get("story", ""))
    sound = smart_para(entry.get("sound_bite", ""))
    # Use a spoken-natural intro. Readers can use the bold ticker visually;
    # listeners hear a sentence.
    header = f"{name} — ticker {ticker}."
    lines = [header]
    if big:
        lines.append(big)
    if story:
        lines.append(story)
    if sound:
        lines.append(f"Memorable line: {sound}")
    return "\n\n".join(lines)


def _extract_tickers_in_text(text: str, companies_data: dict) -> set:
    """Find every ticker mentioned in a piece of text, either by company name
    (from study.json) or by the (TICKER) parenthetical convention used in the
    source prose."""
    mentioned = set()
    # (TICKER) parentheticals
    for m in re.finditer(r'\(([A-Z]{1,6}(?:\.[A-Z])?)\)', text):
        t = m.group(1)
        if t in companies_data:
            mentioned.add(t)
    # Company names from study.json
    for ticker, entry in companies_data.items():
        name = (entry.get("name") or "").strip()
        # Skip very short names (2-3 chars) that would cause false positives
        # in normal English prose ("GE", "MP", "WT", etc.). The (TICKER)
        # parenthetical pattern above still catches them anyway.
        if len(name) < 4:
            continue
        if re.search(r'\b' + re.escape(name) + r'\b', text):
            mentioned.add(ticker)
    return mentioned


COMPARISON_OK = {"MDGL", "RVMD"}


def filter_intro_for_fund(intro_paragraphs: list, held_tickers: set, companies_data: dict) -> list:
    """Aggressive paragraph-level filter: drop any district-intro paragraph
    that mentions a company not held in the current fund.

    Rationale: district intros describe what's in a district, so any mentioned
    company reads as "we own this." Simple, hard rule: if a paragraph names
    a company not held, drop the whole paragraph. Thematic paragraphs with
    no company mentions always survive.

    The user's stated preference: "don't want to look stupid presenting
    something we don't own in the fund." Strict wins over lossy nuance.

    (This only applies to district INTROS. Company narratives — where a
    company's own story may reference customers/partners/competitors by
    name — are not filtered; those mentions are legitimate business context,
    not ownership claims.)
    """
    out_paras = []
    for para in intro_paragraphs:
        mentioned = _extract_tickers_in_text(para, companies_data)
        non_held = mentioned - held_tickers - COMPARISON_OK
        if non_held:
            continue  # drop the whole paragraph
        out_paras.append(para)
    return out_paras


def render_district_section(d_key: str, d_meta: dict, companies_in_order: list, companies_data: dict, held_filter: set = None) -> str:
    """One district section: district intro + all its companies.

    If held_filter is provided (a set of tickers held in the current fund),
    the district intro is filtered to drop sentences that mention only
    companies not in held_filter. For fund-level exports, pass the fund's
    held set. For cross-fund exports (tour/universe), pass None to keep the
    intro unfiltered.
    """
    lines = []
    lines.append(f"\n\n--- {d_meta.get('title', '').upper()} ---")
    sub = d_meta.get("subtitle", "")
    if sub:
        lines.append(sub)

    intro_paras = d_meta.get("intro", [])
    if held_filter is not None:
        intro_paras = filter_intro_for_fund(intro_paras, held_filter, companies_data)
    for p in intro_paras:
        lines.append("")
        lines.append(smart_para(p))

    # Companies
    for t in companies_in_order:
        entry = companies_data.get(t)
        if not entry:
            continue
        lines.append("")
        lines.append(render_company(t, entry))
    return "\n".join(lines)


def render_fund_document(fund_slug: str, fund_label: str, study: dict, holdings: list) -> str:
    """Full narrative document for one fund — ready to upload to NotebookLM."""
    lines = []
    fi = study.get("fund_intros", {}).get(fund_slug, {})
    tagline = fi.get("tagline", "")
    story_paras = fi.get("story", [])

    lines.append(f"THE CITY OF THE FUTURE — {fund_label.upper()}")
    lines.append("=" * 60)
    if tagline:
        lines.append("")
        lines.append(tagline)
    for p in story_paras:
        lines.append("")
        lines.append(smart_para(p))

    # Group holdings by district
    companies = study["companies"]
    districts = study["districts"]
    district_order = study["district_order"]
    acts = study.get("acts", [])

    by_district = {d: [] for d in district_order}
    for t in holdings:
        entry = companies.get(t)
        if entry:
            d = entry.get("district")
            if d in by_district:
                by_district[d].append(t)

    # Walk acts, then districts within each act.
    # Pass the fund's held set to the district renderer so district intros
    # drop sentences that mention companies not actually held in this fund.
    held_set = set(holdings)
    for act in acts:
        act_district_keys = [d for d in act.get("districts", []) if by_district.get(d)]
        if not act_district_keys:
            continue
        lines.append("")
        lines.append("")
        lines.append(f"==== {act.get('title', '').upper()} ====")
        if act.get("subtitle"):
            lines.append(act.get("subtitle"))
        for d_key in act_district_keys:
            comps = sorted(by_district[d_key])
            lines.append(render_district_section(d_key, districts[d_key], comps, companies, held_filter=held_set))

    # Closing
    lines.append("")
    lines.append("")
    lines.append(f"That's the {fund_label} fund — {len(holdings)} holdings across {sum(1 for d in district_order if by_district[d])} districts of the city.")

    return "\n".join(lines)


def render_universe_document(study: dict, all_holdings_by_fund: dict) -> str:
    """One giant document covering every company across every fund.
    Each company shows which funds hold it."""
    lines = []
    lines.append("THE CITY OF THE FUTURE — THE FULL UNIVERSE")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Every name we own across all five innovation growth funds, organized by district.")

    # Ticker → list of fund labels
    ticker_to_funds = {}
    for slug, label in FUNDS:
        for t in all_holdings_by_fund[slug]:
            ticker_to_funds.setdefault(t, []).append(label)

    companies = study["companies"]
    districts = study["districts"]
    district_order = study["district_order"]
    acts = study.get("acts", [])

    by_district = {d: [] for d in district_order}
    for t in ticker_to_funds.keys():
        entry = companies.get(t)
        if entry:
            d = entry.get("district")
            if d in by_district:
                by_district[d].append(t)

    for act in acts:
        act_district_keys = [d for d in act.get("districts", []) if by_district.get(d)]
        if not act_district_keys:
            continue
        lines.append("")
        lines.append("")
        lines.append(f"==== {act.get('title', '').upper()} ====")
        if act.get("subtitle"):
            lines.append(act.get("subtitle"))
        for d_key in act_district_keys:
            comps = sorted(by_district[d_key])
            # Build with fund attribution
            d_meta = districts[d_key]
            lines.append("")
            lines.append(f"--- {d_meta.get('title', '').upper()} ---")
            sub = d_meta.get("subtitle", "")
            if sub:
                lines.append(sub)
            for p in d_meta.get("intro", []):
                lines.append("")
                lines.append(smart_para(p))
            for t in comps:
                entry = companies[t]
                funds = ticker_to_funds.get(t, [])
                fund_note = ""
                if funds:
                    fund_note = f" (Held in: {', '.join(funds)}.)"
                lines.append("")
                # Start with the regular company block but append fund note
                base = render_company(t, entry)
                lines.append(base + fund_note)

    lines.append("")
    lines.append(f"That's the full city — {len(ticker_to_funds)} unique companies across the five funds.")
    return "\n".join(lines)


def render_districts_only(study: dict) -> str:
    """Short document: just the district intros, no company-level detail.
    Good for a quick 5-8 minute podcast overview of the whole city concept."""
    lines = []
    lines.append("THE CITY OF THE FUTURE — A GUIDED TOUR")
    lines.append("=" * 60)
    lines.append("")
    lines.append("A narrative tour through the districts of the city of the future — no individual company details, just how the whole story fits together.")

    districts = study["districts"]
    acts = study.get("acts", [])
    for act in acts:
        if not act.get("districts"):
            continue
        lines.append("")
        lines.append("")
        lines.append(f"==== {act.get('title', '').upper()} ====")
        if act.get("subtitle"):
            lines.append(act.get("subtitle"))
        for d_key in act["districts"]:
            d_meta = districts.get(d_key)
            if not d_meta:
                continue
            lines.append("")
            lines.append(f"--- {d_meta.get('title', '').upper()} ---")
            sub = d_meta.get("subtitle", "")
            if sub:
                lines.append(sub)
            for p in d_meta.get("intro", []):
                lines.append("")
                lines.append(smart_para(p))

    return "\n".join(lines)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    study = load_study()
    all_holdings = {slug: load_holdings(slug) for slug, _ in FUNDS}

    # Per-fund documents
    for slug, label in FUNDS:
        doc = render_fund_document(slug, label, study, all_holdings[slug])
        path = OUT / f"{slug}.txt"
        path.write_text(doc)
        words = len(doc.split())
        print(f"Wrote {path.relative_to(ROOT)}  ({words:,} words)")

    # Full universe
    universe = render_universe_document(study, all_holdings)
    up = OUT / "all-funds-universe.txt"
    up.write_text(universe)
    print(f"Wrote {up.relative_to(ROOT)}  ({len(universe.split()):,} words)")

    # District-only tour
    tour = render_districts_only(study)
    tp = OUT / "all-funds-district-tour.txt"
    tp.write_text(tour)
    print(f"Wrote {tp.relative_to(ROOT)}  ({len(tour.split()):,} words)")


if __name__ == "__main__":
    main()
