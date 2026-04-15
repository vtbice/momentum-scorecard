#!/usr/bin/env python3
"""
build_guide.py — Generates a branded HTML study guide for a given fund.

Usage:
    python3 scripts/build_guide.py small-cap
    python3 scripts/build_guide.py small-cap --date 2026-04-15

Reads:
    data/holdings/<fund>.csv      -- list of tickers
    data/study.json               -- fund intros, district metadata+intros, per-ticker data

Writes:
    guides/<fund>-<date>.html     -- branded study guide (print-friendly to PDF)
    guides/<fund>-latest.html     -- most recent
"""
import argparse
import csv
import html
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
GUIDES = ROOT / "guides"


def load_holdings(fund: str):
    path = DATA / "holdings" / f"{fund}.csv"
    with path.open() as f:
        reader = csv.DictReader(f)
        return [row["ticker"].strip() for row in reader if row["ticker"].strip() and row["ticker"].strip() != "$CASH"]


def load_study():
    with (DATA / "study.json").open() as f:
        return json.load(f)


def esc(s: str) -> str:
    return html.escape(s or "", quote=False)


def build_html(fund: str, as_of: str, holdings: list, study: dict) -> str:
    companies = study["companies"]
    districts = study["districts"]
    district_order = study["district_order"]
    fund_intro = study.get("fund_intros", {}).get(fund, {})

    # Group holdings by district
    by_district = {d: [] for d in district_order}
    unassigned = []
    for ticker in holdings:
        entry = companies.get(ticker)
        if not entry:
            unassigned.append(ticker)
            continue
        d = entry.get("district", "unassigned")
        if d in by_district:
            by_district[d].append((ticker, entry))
        else:
            unassigned.append(ticker)

    total = len(holdings)
    covered = sum(1 for t in holdings if companies.get(t))
    districts_shown = sum(1 for d in district_order if by_district[d])
    fund_display = fund.replace("-", " ").title()

    # Fund intro HTML
    fund_intro_html = ""
    if fund_intro:
        tagline = esc(fund_intro.get("tagline", ""))
        story_paras = "".join(f"<p>{esc(p)}</p>" for p in fund_intro.get("story", []))
        fund_intro_html = f"""
        <section class="fund-intro">
          <div class="fund-intro-tagline">{tagline}</div>
          <div class="fund-intro-body">{story_paras}</div>
        </section>
        """

    # District sections
    sections_html = []
    for d in district_order:
        bucket = by_district[d]
        if not bucket:
            continue
        bucket.sort(key=lambda x: x[0])
        dmeta = districts[d]

        intro_paras = "".join(f"<p>{esc(p)}</p>" for p in dmeta.get("intro", []))

        cards = []
        for ticker, entry in bucket:
            sound = entry.get("sound_bite") or ""
            cards.append(f"""
            <article class="card" id="{esc(ticker)}">
              <header class="card-head">
                <span class="ticker">{esc(ticker)}</span>
                <span class="company-name">{esc(entry.get('name', ''))}</span>
              </header>
              <p class="big-picture">{esc(entry.get('big_picture', ''))}</p>
              <div class="story">{esc(entry.get('story', ''))}</div>
              {f'<p class="sound-bite">&ldquo;{esc(sound)}&rdquo;</p>' if sound else ''}
            </article>
            """)

        sections_html.append(f"""
        <section class="district" id="district-{d}">
          <div class="district-header">
            <h2 class="district-title">{esc(dmeta['title'])} <span class="district-count">{len(bucket)}</span></h2>
            <div class="district-subtitle">{esc(dmeta.get('subtitle', ''))}</div>
          </div>
          <div class="district-intro">
            {intro_paras}
          </div>
          <div class="card-grid">
            {''.join(cards)}
          </div>
        </section>
        """)

    # Unassigned holdings banner (if any)
    unassigned_html = ""
    if unassigned:
        items = ", ".join(esc(t) for t in unassigned)
        unassigned_html = f"""
        <div class="warning-banner">
          <strong>Heads up:</strong> {len(unassigned)} holding(s) in this fund have no entry in <code>data/study.json</code> yet: {items}. Add them and re-run the builder.
        </div>
        """

    # Table of contents grouped by district
    toc_sections = []
    for d in district_order:
        bucket = by_district[d]
        if not bucket:
            continue
        bucket_sorted = sorted(bucket, key=lambda x: x[0])
        items = "".join(
            f'<a href="#{esc(t)}" class="toc-item"><span class="toc-ticker">{esc(t)}</span><span class="toc-name">{esc(e.get("name", ""))}</span></a>'
            for t, e in bucket_sorted
        )
        toc_sections.append(f"""
        <div class="toc-district">
          <a href="#district-{d}" class="toc-district-title">{esc(districts[d]['title'])}</a>
          <div class="toc-district-items">{items}</div>
        </div>
        """)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(fund_display)} Study Guide — {esc(as_of)}</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    font-family: 'DM Sans', sans-serif;
    background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
    color: #0f172a;
    line-height: 1.65;
    font-size: 15px;
  }}
  header.site-head {{
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    padding: 28px 32px;
    border-bottom: 3px solid #10b981;
    color: white;
  }}
  .header-inner {{
    max-width: 1100px;
    margin: 0 auto;
    text-align: center;
  }}
  .kicker {{
    font-size: 12px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #10b981;
    margin-bottom: 8px;
    font-weight: 500;
  }}
  .header-title {{
    font-family: 'Fraunces', serif;
    font-size: 38px;
    font-weight: 700;
    letter-spacing: 0.01em;
  }}
  .header-sub {{
    font-size: 14px;
    color: #94a3b8;
    margin-top: 8px;
  }}
  main {{
    max-width: 1100px;
    margin: 32px auto 64px;
    padding: 0 24px;
  }}

  /* Fund intro */
  .fund-intro {{
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: #f1f5f9;
    border-radius: 14px;
    padding: 36px 40px;
    margin-bottom: 40px;
    border: 1px solid #1e293b;
    box-shadow: 0 4px 24px rgba(15, 23, 42, 0.12);
  }}
  .fund-intro-tagline {{
    font-family: 'Fraunces', serif;
    font-size: 22px;
    font-style: italic;
    color: #10b981;
    margin-bottom: 18px;
    letter-spacing: 0.01em;
  }}
  .fund-intro-body p {{
    font-size: 15.5px;
    line-height: 1.75;
    margin-bottom: 14px;
    color: #e2e8f0;
  }}
  .fund-intro-body p:last-child {{ margin-bottom: 0; }}

  /* Summary stats */
  .summary {{
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 32px;
    display: flex;
    gap: 40px;
    flex-wrap: wrap;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }}
  .stat {{ display: flex; flex-direction: column; }}
  .stat-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: #64748b; font-weight: 500; }}
  .stat-value {{ font-family: 'Fraunces', serif; font-size: 32px; font-weight: 600; color: #0f172a; margin-top: 2px; }}
  .stat-value.accent {{ color: #10b981; }}

  .warning-banner {{
    background: #fef3c7;
    border: 1px solid #fbbf24;
    border-radius: 8px;
    padding: 12px 18px;
    margin-bottom: 24px;
    font-size: 13px;
    color: #78350f;
  }}
  .warning-banner code {{ background: rgba(0,0,0,0.08); padding: 1px 5px; border-radius: 3px; font-size: 12px; }}

  /* Table of contents */
  .toc {{
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 48px;
  }}
  .toc h3 {{
    font-family: 'Fraunces', serif;
    font-size: 20px;
    margin-bottom: 18px;
    color: #0f172a;
  }}
  .toc-district {{ margin-bottom: 18px; }}
  .toc-district:last-child {{ margin-bottom: 0; }}
  .toc-district-title {{
    display: block;
    font-family: 'Fraunces', serif;
    font-size: 14px;
    font-weight: 600;
    color: #10b981;
    text-decoration: none;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
  }}
  .toc-district-title:hover {{ color: #059669; }}
  .toc-district-items {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 2px 16px;
  }}
  .toc-item {{
    text-decoration: none;
    color: #0f172a;
    font-size: 12.5px;
    padding: 3px 0;
    display: flex;
    gap: 8px;
  }}
  .toc-item:hover .toc-ticker {{ color: #059669; }}
  .toc-ticker {{ font-weight: 600; color: #10b981; min-width: 52px; }}
  .toc-name {{ color: #475569; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

  /* District sections */
  .district {{
    margin-bottom: 64px;
  }}
  .district-header {{
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 2px solid #10b981;
  }}
  .district-title {{
    font-family: 'Fraunces', serif;
    font-size: 32px;
    font-weight: 600;
    color: #0f172a;
    display: flex;
    align-items: baseline;
    gap: 14px;
  }}
  .district-subtitle {{
    font-size: 14px;
    color: #64748b;
    margin-top: 4px;
    font-style: italic;
  }}
  .district-count {{
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    font-weight: 500;
    color: #64748b;
    background: #f1f5f9;
    padding: 3px 12px;
    border-radius: 999px;
  }}
  .district-intro {{
    background: #f8fafc;
    border-left: 3px solid #10b981;
    padding: 18px 22px;
    border-radius: 4px;
    margin-bottom: 24px;
  }}
  .district-intro p {{
    font-size: 14.5px;
    line-height: 1.75;
    color: #334155;
    margin-bottom: 12px;
  }}
  .district-intro p:last-child {{ margin-bottom: 0; }}

  /* Cards */
  .card-grid {{
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}
  .card {{
    background: white;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #10b981;
    border-radius: 10px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }}
  .card-head {{
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }}
  .ticker {{
    font-family: 'Fraunces', serif;
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: 0.02em;
  }}
  .company-name {{
    font-size: 14px;
    color: #64748b;
    font-weight: 500;
  }}
  .big-picture {{
    font-size: 15px;
    font-weight: 500;
    color: #0f172a;
    margin-bottom: 12px;
    font-style: italic;
  }}
  .story {{
    font-size: 14.5px;
    color: #334155;
    line-height: 1.75;
  }}
  .sound-bite {{
    margin-top: 14px;
    padding: 10px 16px;
    background: #ecfdf5;
    border-left: 3px solid #10b981;
    border-radius: 4px;
    font-family: 'Fraunces', serif;
    font-size: 15px;
    font-style: italic;
    color: #065f46;
  }}

  footer {{
    text-align: center;
    padding: 28px;
    color: #64748b;
    font-size: 12px;
  }}

  /* Print / PDF styles */
  @media print {{
    body {{ background: white; font-size: 11pt; }}
    header.site-head, .fund-intro {{
      background: #0f172a !important;
      color: white;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}
    main {{ margin: 16px auto; }}
    .toc {{ page-break-after: always; }}
    .district {{ page-break-before: auto; page-break-inside: auto; }}
    .district-intro {{ page-break-inside: avoid; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .card {{ page-break-inside: avoid; box-shadow: none; }}
    .sound-bite {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    a {{ color: inherit; text-decoration: none; }}
  }}
</style>
</head>
<body>
<header class="site-head">
  <div class="header-inner">
    <div class="kicker">Innovation Growth Funds</div>
    <h1 class="header-title">{esc(fund_display)} <span style="color:#10b981;">Study Guide</span></h1>
    <div class="header-sub">As of {esc(as_of)}</div>
  </div>
</header>

<main>
  {fund_intro_html}

  <section class="summary">
    <div class="stat">
      <span class="stat-label">Holdings</span>
      <span class="stat-value">{total}</span>
    </div>
    <div class="stat">
      <span class="stat-label">Written Up</span>
      <span class="stat-value accent">{covered}</span>
    </div>
    <div class="stat">
      <span class="stat-label">Districts</span>
      <span class="stat-value">{districts_shown}</span>
    </div>
    <div class="stat">
      <span class="stat-label">As Of</span>
      <span class="stat-value" style="font-size:20px;padding-top:8px;">{esc(as_of)}</span>
    </div>
  </section>

  {unassigned_html}

  <nav class="toc">
    <h3>Quick Index</h3>
    {''.join(toc_sections)}
  </nav>

  {''.join(sections_html)}
</main>

<footer>
  Innovation Growth &middot; {esc(fund_display)} Study Guide &middot; {esc(as_of)} &middot;
  Tip: Cmd+P to save as PDF for offline reading
</footer>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fund", help="Fund name matching data/holdings/<fund>.csv (e.g. small-cap)")
    parser.add_argument("--date", default=str(date.today()), help="As-of date (default: today)")
    args = parser.parse_args()

    holdings = load_holdings(args.fund)
    study = load_study()
    html_out = build_html(args.fund, args.date, holdings, study)

    GUIDES.mkdir(parents=True, exist_ok=True)
    dated = GUIDES / f"{args.fund}-{args.date}.html"
    latest = GUIDES / f"{args.fund}-latest.html"
    dated.write_text(html_out)
    latest.write_text(html_out)
    print(f"Wrote {dated}")
    print(f"Wrote {latest}")


if __name__ == "__main__":
    main()
