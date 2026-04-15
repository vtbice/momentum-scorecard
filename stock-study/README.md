# The City of the Future

A narrative-driven, multi-page guide to all holdings across the five Innovation
Growth funds — plus a searchable directory of the ~1,200-name watchlist.

## What this is

Every company you own across the five funds has a narrative in the voice of
*The City of the Future*, organized into 11 districts grouped into 4 acts:

**Act I — Components**
- The Chip Works · The Wires · The Machine Shop

**Act II — Built & Powered**
- The Construction Yards · The Power Plant

**Act III — Money & Code**
- The Financial District · The Software Layer

**Act IV — The Services**
- The Arsenal · The Clinic · The Research Labs · Main Street

Each company card has a narrative, a sound bite, an embedded TradingView chart
with a 30-week moving average (= 150-day equivalent), and a deep-link to
StockCharts for users who have that account.

## Layout

```
stock-study/
├── data/
│   ├── holdings/           # one CSV per fund (ticker list)
│   ├── study.json          # single source of truth: districts, acts, narratives, fund intros
│   └── source/             # original raw input docs (preserved for reference)
├── scripts/
│   ├── build_site.py       # generates the static site from data/
│   └── admin.py            # local admin server for editing holdings
├── site/                   # the generated static site (index.html, 5 fund pages, watchlist)
└── README.md               # this file
```

The watchlist reads `../tickers.csv` (shared with the Momentum Scorecard repo,
so the two systems stay in sync automatically).

---

## Workflow: adding and removing tickers

### The easy way (admin server)

```bash
cd stock-study
python3 scripts/admin.py
```

This starts a local server at `http://localhost:8765/` and opens it in your
browser. You'll see the normal site with an **Edit** button in the bottom-right
corner. Click it to enter edit mode, then:

- **On any fund page** → an "Add ticker" box appears in a green bar at the top,
  and every card gets a small red **✕ Remove** button
- **On the Overview page** → same add box (with a fund selector), and every
  card gets a yellow **↓ Demote** button that removes the ticker from *all*
  funds but keeps it on the watchlist
- **On the Watchlist page** → add box, and every row gets a remove button

Every change is saved to the right CSV instantly, the site is rebuilt, and the
page reloads with the update visible. When you're done, press `Ctrl+C` in the
terminal to stop the server.

**Behavior rules:**
- Adding a ticker to a fund also adds it to the watchlist if it's not there
- Removing a ticker from its *last* fund auto-tags it as `status: former_holding`
  in `study.json` with today's date
- Removing a ticker from the watchlist is blocked if any fund still holds it

### The manual way (editing CSVs)

If you don't want to run the admin server, just edit the CSVs directly:

- `data/holdings/<fund>.csv` — one ticker per line
- `../tickers.csv` — the watchlist (shared with the Momentum Scorecard)

Then rebuild:

```bash
python3 scripts/build_site.py
```

The build will warn you if any fund holds a ticker with no narrative in
`study.json`.

---

## Adding a brand-new name (not just reordering)

If the ticker is genuinely new and has no narrative yet:

1. **Add it to the fund CSV** (via admin server or manually).
2. Open `data/study.json` and add a new entry under `"companies"` with at
   minimum `name`, `district`, `big_picture`, `story`, and `sound_bite`.
3. Rebuild the site. The card will appear in the right district.

A small helper is on the roadmap to draft new narratives automatically.

---

## Publishing the site

The `site/` folder is a standard static site. To publish as a shared URL for
the team, point any static host (GitHub Pages, Netlify, S3, etc.) at the
`site/` folder. The admin server only runs locally, and its admin controls
never ship to the published version — `admin.js` is served *only* by the local
admin server, so the public site is read-only.

---

## Features in the live site

- **Overview page** — all 207 holdings in one universe view with fund-membership
  chips showing which of the 5 funds hold each name
- **5 fund pages** — per-fund guide with intro, table of contents, district
  walkthroughs, and cards
- **Watchlist page** — searchable/filterable table of the full ~1,234-ticker
  universe with status filters
- **Search modal** — press `/` or click the search box in the header, type any
  ticker or company name, click a result, and a modal opens with the full
  narrative + chart + StockCharts link. Works from any page.
- **Lazy-loaded TradingView charts** — only render when they scroll into view
- **Print-friendly PDF mode** — `Cmd+P` gives a clean PDF with no chrome

---

## File index

- `scripts/build_site.py` — site generator
- `scripts/admin.py` — admin server (local only)
- `data/study.json` — all narratives, district metadata, fund intros, acts
- `data/holdings/*.csv` — per-fund ticker lists
- `site/*.html` — generated pages
