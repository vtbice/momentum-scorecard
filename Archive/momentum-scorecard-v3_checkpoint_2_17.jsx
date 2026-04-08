import { useState, useMemo } from "react";
import { TrendingUp, TrendingDown, Minus, ChevronRight, ChevronDown, Search, X, ArrowUpRight, ArrowDownRight, Activity, BarChart3, Layers, Shield, Info, ArrowUp, ArrowDown, DollarSign, Zap, Eye, Target, AlertTriangle, ChevronUp } from "lucide-react";

// ============================================================
// PROSPER MOMENTUM SCORECARD — V3: Live Pipeline Data
// Market Health (Telescope) + Stock Momentum (Microscope)
// ============================================================

const C = {
  emerald: "#10b981", emeraldDark: "#059669", emeraldLight: "#d1fae5", emeraldMuted: "#065f46",
  red: "#ef4444", redLight: "#fecaca", redMuted: "#991b1b",
  amber: "#f59e0b", amberLight: "#fef3c7", amberMuted: "#92400e",
  indigo: "#6366f1", indigoLight: "#e0e7ff",
  blue: "#3b82f6", blueLight: "#dbeafe", blueMuted: "#1e40af",
  purple: "#a855f7", purpleLight: "#f3e8ff",
  rose: "#fb7185",
  gold: "#d97706",
  s50: "#f8fafc", s100: "#f1f5f9", s200: "#e2e8f0", s300: "#cbd5e1",
  s400: "#94a3b8", s500: "#64748b", s600: "#475569", s700: "#334155",
  s800: "#1e293b", s900: "#0f172a",
};

const TREND_COLORS = {
  Uptrend:   { bg: "#d1fae5", text: "#065f46", fill: "#10b981" },
  Pullback:  { bg: "#fef3c7", text: "#92400e", fill: "#f59e0b" },
  Downtrend: { bg: "#fecaca", text: "#991b1b", fill: "#ef4444" },
  Snapback:  { bg: "#dbeafe", text: "#1e40af", fill: "#3b82f6" },
};

const TIER_COLOR = (t) => t <= 2 ? C.emerald : t <= 4 ? C.emeraldDark : t <= 6 ? C.amber : t <= 8 ? C.red : "#991b1b";

// ============================================================
// DATA — Live from Python Pipeline (scorecard_data.json)
// Generated: 2/17/26 — 49 stocks, FRED + yfinance
// ============================================================

const MARKET = {
  date: "2/17/26",
  overallScore: "Neutral",
  healthScore: 60,
  healthTotal: 90,
  healthLabel: "Cautiously Optimistic",
  // --- Health wins/misses from pipeline ---
  healthWins: [
    { label: "Labor Market Strong (Unemp 4.3% < 5%)", weight: 5, cat: "Macro" },
    { label: "GDP Growth Solid (4.4% > 2%)", weight: 5, cat: "Macro" },
    { label: "Inflation Contained (2.8% < 3%)", weight: 5, cat: "Macro" },
    { label: "Credit Markets Calm (HY 2.92% < 4%)", weight: 5, cat: "Macro" },
    { label: "Earnings Growing (8.5% > 5%)", weight: 5, cat: "Fundamental" },
    { label: "Margins Healthy (12.2% > 11%)", weight: 5, cat: "Fundamental" },
    { label: "Revisions Positive (1.15x > 1.0)", weight: 5, cat: "Fundamental" },
    { label: "Free Cash Flow Healthy (3.8% > 3.5%)", weight: 5, cat: "Fundamental" },
    { label: "Long-Term Uptrend (S&P 6,779 > 4yr MA 5,082)", weight: 10, cat: "Technical" },
    { label: "Medium-Term Uptrend (S&P 6,779 > 150d MA 6,689)", weight: 5, cat: "Technical" },
    { label: "Sentiment Supportive (P/C 0.75 < 1.0)", weight: 5, cat: "Technical" },
  ],
  healthMisses: [
    { label: "Consumer Confidence Weak (52.9 < 70)", weight: 5, cat: "Macro" },
    { label: "Mortgage Rates Elevated (6.09% > 6%)", weight: 5, cat: "Macro" },
    { label: "Valuation Stretched (P/E 21.5 > 20)", weight: 5, cat: "Fundamental" },
    { label: "Narrow Breadth (57.1% < 60%)", weight: 10, cat: "Technical" },
    { label: "Volatility Elevated (VIX 22.58 > 20)", weight: 5, cat: "Technical" },
  ],
  // --- Market Trend ---
  // Positive: price above positive-sloped 150 SMA
  // Neutral: price below positive-sloped OR above negative-sloped
  // Negative: price below negative-sloped 150 SMA
  trend: {
    score: "Positive",  // R3K above + slope positive = Positive
    r3kVs150MA: "Above",
    maSlope: "Positive",
  },
  // --- Breadth ---
  breadth: {
    pctAbove: 57.1,
    r3kPrice: 3866.39,
    r3kMA150: 3802.62,
    fwdReturns: [
      { range: "Above 90%", pctTime: 0.8, fwd: 10.7 },
      { range: "80–90%", pctTime: 9.3, fwd: 13.2 },
      { range: "70–80%", pctTime: 15.2, fwd: 13.9 },
      { range: "60–70%", pctTime: 22.3, fwd: 12.6 },
      { range: "50–60%", pctTime: 18.9, fwd: 6.9 },
      { range: "40–50%", pctTime: 14.9, fwd: 6.7 },
      { range: "30–40%", pctTime: 8.7, fwd: 6.2 },
      { range: "20–30%", pctTime: 4.7, fwd: 9.5 },
      { range: "10–20%", pctTime: 3.8, fwd: 22.2 },
      { range: "Below 10%", pctTime: 1.4, fwd: 44.1 },
    ],
  },
  // --- Macro (FRED live data) ---
  macro: {
    gdp: 4.4, employment: 4.3, inflation: 2.8,
    sentiment: 52.9, fedFunds: 3.64,
    tenYear: 4.09, twoYear: 3.47,
    hySpread: 2.92, igSpread: 0.99,
    oil: 62.0, dxy: 97.5,
    mortgage: 6.09, gasPrice: 2.90,
    joblessClaims: 227,
    wageGrowth: 37.17,
    fiscalPolicy: "Supportive",
    monetaryPolicy: "Easing",
    geopolitical: "Moderate",
  },
  // --- Fundamental (manual quarterly update) ---
  fundamental: {
    salesGrowth: 4.1, earningsGrowth: 8.5,
    earningsBeat: 72, salesBeat: 64,
    revisions: 1.15,
    netMargin: 12.2, marginTrend: "Stable",
    fcfYield: 3.8,
    forwardPE: 21.5, historicalPE: 17.8, pegRatio: 1.4,
    capex: 4.7, buybackYield: 2.1, divYield: 1.4, leverage: 1.6,
  },
  // --- Technical (live) ---
  technical: {
    sp500: 6778.99, sp500MA4yr: 5081.99, sp500MA150: 6688.62,
    vix: 22.58, putCall: 0.75, aaii: 42.5,
  },
  synthesis: {
    equities: { view: "Neutral", color: C.amber, desc: "Solid earnings and long-term uptrend intact, but narrowing breadth, elevated VIX, and stretched valuations call for selectivity. Favor momentum leaders in top tiers." },
    fixedIncome: { view: "Neutral", color: C.amber, desc: "Yields are attractive with a normal curve. Focus on quality duration as the Fed eases. High yield spreads are calm but tight — avoid reaching for yield." },
    cash: { view: "Underweight", color: C.red, desc: "With inflation at 2.8% and real rates positive, excess cash creates drag. Deploy into risk assets during pullbacks — but keep dry powder given VIX above 20." },
  },
};

// Sectors — from pipeline
const SECTORS = [
  { name: "Industrials", n: 2, up: 100.0, pb: 0.0, dn: 0.0, sb: 0.0, rm: 89.0 },
  { name: "Healthcare", n: 5, up: 80.0, pb: 20.0, dn: 0.0, sb: 0.0, rm: 65.2 },
  { name: "Energy", n: 4, up: 75.0, pb: 0.0, dn: 0.0, sb: 25.0, rm: 62.2 },
  { name: "Utilities", n: 3, up: 66.7, pb: 0.0, dn: 0.0, sb: 33.3, rm: 61.3 },
  { name: "Consumer Defensive", n: 5, up: 60.0, pb: 0.0, dn: 0.0, sb: 40.0, rm: 50.8 },
  { name: "Consumer Cyclical", n: 6, up: 50.0, pb: 16.7, dn: 33.3, sb: 0.0, rm: 30.2 },
  { name: "Technology", n: 11, up: 36.4, pb: 27.3, dn: 36.4, sb: 0.0, rm: 55.0 },
  { name: "Communication Services", n: 4, up: 25.0, pb: 0.0, dn: 75.0, sb: 0.0, rm: 40.2 },
  { name: "Financial Services", n: 9, up: 22.2, pb: 33.3, dn: 44.4, sb: 0.0, rm: 40.9 },
];

// Stocks — all 49 from pipeline (sorted by market cap)
const STOCKS = [
  { t: "NVDA", co: "NVIDIA Corporation", sec: "Technology", ind: "Semiconductors", px: 182.81, mc: 4378199, tr: "Uptrend", rm: 80, ti: 4, ov: 0.2, p12: 135.29, p1: 187.05 },
  { t: "AAPL", co: "Apple Inc.", sec: "Technology", ind: "Consumer Electronics", px: 255.78, mc: 3819550, tr: "Uptrend", rm: 43, ti: 7, ov: 1.5, p12: 241.53, p1: 258.21 },
  { t: "GOOGL", co: "Alphabet Inc.", sec: "Communication Services", ind: "Internet Content & Information", px: 305.72, mc: 3606963, tr: "Uptrend", rm: 94, ti: 2, ov: 14.4, p12: 186.14, p1: 332.78 },
  { t: "MSFT", co: "Microsoft Corporation", sec: "Technology", ind: "Software - Infrastructure", px: 401.32, mc: 2948498, tr: "Downtrend", rm: 39, ti: 8, ov: -18.8, p12: 410.54, p1: 456.66 },
  { t: "AMZN", co: "Amazon.com, Inc.", sec: "Consumer Cyclical", ind: "Internet Retail", px: 198.79, mc: 2142046, tr: "Pullback", rm: 16, ti: 10, ov: -13.1, p12: 230.37, p1: 238.18 },
  { t: "META", co: "Meta Platforms, Inc.", sec: "Communication Services", ind: "Internet Content & Information", px: 639.77, mc: 1597895, tr: "Downtrend", rm: 20, ti: 9, ov: -8.0, p12: 728.56, p1: 620.80 },
  { t: "AVGO", co: "Broadcom Inc.", sec: "Technology", ind: "Semiconductors", px: 325.17, mc: 1539705, tr: "Pullback", rm: 86, ti: 3, ov: -3.2, p12: 235.80, p1: 343.02 },
  { t: "TSLA", co: "Tesla, Inc.", sec: "Consumer Cyclical", ind: "Auto Manufacturers", px: 417.44, mc: 1508009, tr: "Uptrend", rm: 63, ti: 5, ov: 2.6, p12: 355.94, p1: 438.57 },
  { t: "WMT", co: "Walmart Inc.", sec: "Consumer Defensive", ind: "Discount Stores", px: 133.89, mc: 1040736, tr: "Uptrend", rm: 76, ti: 4, ov: 24.8, p12: 105.05, p1: 119.20 },
  { t: "LLY", co: "Eli Lilly and Company", sec: "Healthcare", ind: "Drug Manufacturers - General", px: 1040.00, mc: 992865, tr: "Uptrend", rm: 67, ti: 5, ov: 16.3, p12: 871.86, p1: 1032.97 },
  { t: "JPM", co: "JPMorgan Chase & Co.", sec: "Financial Services", ind: "Banks - Diversified", px: 302.55, mc: 834945, tr: "Pullback", rm: 49, ti: 6, ov: -1.5, p12: 275.44, p1: 324.12 },
  { t: "V", co: "Visa Inc.", sec: "Financial Services", ind: "Credit Services", px: 325.66, mc: 552281, tr: "Downtrend", rm: 31, ti: 8, ov: -5.5, p12: 351.57, p1: 343.62 },
  { t: "JNJ", co: "Johnson & Johnson", sec: "Healthcare", ind: "Drug Manufacturers - General", px: 243.45, mc: 579505, tr: "Uptrend", rm: 84, ti: 3, ov: 26.7, p12: 153.91, p1: 209.77 },
  { t: "XOM", co: "Exxon Mobil Corporation", sec: "Energy", ind: "Oil & Gas Integrated", px: 148.45, mc: 618768, tr: "Uptrend", rm: 65, ti: 5, ov: 27.0, p12: 107.22, p1: 124.02 },
  { t: "COST", co: "Costco Wholesale Corp.", sec: "Consumer Defensive", ind: "Discount Stores", px: 1015.38, mc: 448999, tr: "Snapback", rm: 24, ti: 9, ov: 7.2, p12: 1072.11, p1: 945.89 },
  { t: "PG", co: "The Procter & Gamble Co.", sec: "Consumer Defensive", ind: "Household Products", px: 78.68, mc: 340021, tr: "Uptrend", rm: 57, ti: 6, ov: 12.4, p12: 69.50, p1: 70.48 },
  { t: "NFLX", co: "Netflix, Inc.", sec: "Communication Services", ind: "Entertainment", px: 76.87, mc: 323041, tr: "Downtrend", rm: 10, ti: 10, ov: -29.0, p12: 104.37, p1: 88.05 },
  { t: "AMD", co: "Advanced Micro Devices, Inc.", sec: "Technology", ind: "Semiconductors", px: 207.32, mc: 320656, tr: "Uptrend", rm: 96, ti: 2, ov: 2.4, p12: 111.81, p1: 227.92 },
  { t: "PLTR", co: "Palantir Technologies Inc.", sec: "Technology", ind: "Software - Infrastructure", px: 131.41, mc: 308536, tr: "Pullback", rm: 53, ti: 6, ov: -23.1, p12: 117.91, p1: 177.07 },
  { t: "MRK", co: "Merck & Co., Inc.", sec: "Healthcare", ind: "Drug Manufacturers - General", px: 121.41, mc: 303331, tr: "Uptrend", rm: 90, ti: 3, ov: 30.2, p12: 84.42, p1: 110.97 },
  { t: "GS", co: "The Goldman Sachs Group, Inc.", sec: "Financial Services", ind: "Capital Markets", px: 905.14, mc: 274840, tr: "Uptrend", rm: 88, ti: 3, ov: 11.2, p12: 648.95, p1: 975.86 },
  { t: "MS", co: "Morgan Stanley", sec: "Financial Services", ind: "Capital Markets", px: 171.15, mc: 272177, tr: "Uptrend", rm: 73, ti: 4, ov: 5.0, p12: 136.84, p1: 191.23 },
  { t: "UNH", co: "UnitedHealth Group Inc.", sec: "Healthcare", ind: "Healthcare Plans", px: 293.19, mc: 262634, tr: "Pullback", rm: 6, ti: 10, ov: -8.4, p12: 531.18, p1: 338.96 },
  { t: "MCD", co: "McDonald's Corporation", sec: "Consumer Cyclical", ind: "Restaurants", px: 327.58, mc: 233284, tr: "Uptrend", rm: 41, ti: 7, ov: 6.5, p12: 310.02, p1: 308.62 },
  { t: "INTC", co: "Intel Corporation", sec: "Technology", ind: "Semiconductors", px: 46.79, mc: 228355, tr: "Uptrend", rm: 98, ti: 2, ov: 35.4, p12: 24.13, p1: 48.32 },
  { t: "PEP", co: "PepsiCo, Inc.", sec: "Consumer Defensive", ind: "Beverages - Non-Alcoholic", px: 165.94, mc: 222384, tr: "Uptrend", rm: 59, ti: 6, ov: 13.1, p12: 144.58, p1: 146.57 },
  { t: "NEE", co: "NextEra Energy, Inc.", sec: "Utilities", ind: "Utilities - Regulated Electric", px: 93.80, mc: 194328, tr: "Uptrend", rm: 82, ti: 3, ov: 17.7, p12: 68.60, p1: 82.19 },
  { t: "BA", co: "The Boeing Company", sec: "Industrials", ind: "Aerospace & Defense", px: 242.96, mc: 187826, tr: "Uptrend", rm: 78, ti: 4, ov: 10.3, p12: 185.44, p1: 247.74 },
  { t: "DIS", co: "The Walt Disney Company", sec: "Communication Services", ind: "Entertainment", px: 105.45, mc: 185505, tr: "Downtrend", rm: 37, ti: 8, ov: -6.5, p12: 109.59, p1: 113.41 },
  { t: "CRM", co: "Salesforce, Inc.", sec: "Technology", ind: "Software - Application", px: 189.72, mc: 175168, tr: "Downtrend", rm: 8, ti: 10, ov: -22.2, p12: 329.85, p1: 233.53 },
  { t: "SCHW", co: "The Charles Schwab Corp.", sec: "Financial Services", ind: "Capital Markets", px: 93.72, mc: 168044, tr: "Pullback", rm: 61, ti: 5, ov: -2.9, p12: 81.57, p1: 102.76 },
  { t: "BLK", co: "BlackRock, Inc.", sec: "Financial Services", ind: "Asset Management", px: 1071.51, mc: 164643, tr: "Pullback", rm: 45, ti: 7, ov: -3.1, p12: 980.30, p1: 1156.65 },
  { t: "UBER", co: "Uber Technologies, Inc.", sec: "Technology", ind: "Software - Application", px: 69.99, mc: 145552, tr: "Downtrend", rm: 18, ti: 10, ov: -21.7, p12: 80.29, p1: 84.38 },
  { t: "SO", co: "The Southern Company", sec: "Utilities", ind: "Utilities - Regulated Electric", px: 94.95, mc: 103262, tr: "Snapback", rm: 47, ti: 7, ov: 3.6, p12: 86.78, p1: 88.78 },
  { t: "DUK", co: "Duke Energy Corporation", sec: "Utilities", ind: "Utilities - Regulated Electric", px: 128.20, mc: 99377, tr: "Uptrend", rm: 55, ti: 6, ov: 5.4, p12: 113.95, p1: 118.90 },
  { t: "NKE", co: "NIKE, Inc.", sec: "Consumer Cyclical", ind: "Footwear & Accessories", px: 63.13, mc: 93309, tr: "Downtrend", rm: 14, ti: 10, ov: -7.7, p12: 73.21, p1: 64.59 },
  { t: "ABNB", co: "Airbnb, Inc.", sec: "Consumer Cyclical", ind: "Travel Services", px: 121.35, mc: 74886, tr: "Downtrend", rm: 12, ti: 10, ov: -4.5, p12: 141.04, p1: 132.60 },
  { t: "SLB", co: "SLB N.V.", sec: "Energy", ind: "Oil & Gas Equipment & Services", px: 50.39, mc: 73129, tr: "Uptrend", rm: 71, ti: 4, ov: 32.8, p12: 42.08, p1: 46.57 },
  { t: "NET", co: "Cloudflare, Inc.", sec: "Technology", ind: "Software - Infrastructure", px: 195.85, mc: 67027, tr: "Pullback", rm: 51, ti: 6, ov: -4.0, p12: 176.50, p1: 184.14 },
  { t: "EOG", co: "EOG Resources, Inc.", sec: "Energy", ind: "Oil & Gas E&P", px: 120.73, mc: 64613, tr: "Snapback", rm: 29, ti: 9, ov: 7.7, p12: 129.02, p1: 108.02 },
  { t: "SNOW", co: "Snowflake Inc.", sec: "Technology", ind: "Software - Application", px: 182.29, mc: 59165, tr: "Downtrend", rm: 33, ti: 8, ov: -18.7, p12: 192.66, p1: 207.74 },
  { t: "COIN", co: "Coinbase Global, Inc.", sec: "Financial Services", ind: "Financial Data & Stock Exchanges", px: 164.32, mc: 44557, tr: "Downtrend", rm: 4, ti: 10, ov: -44.1, p12: 298.11, p1: 239.28 },
  { t: "PYPL", co: "PayPal Holdings, Inc.", sec: "Financial Services", ind: "Credit Services", px: 40.29, mc: 37964, tr: "Downtrend", rm: 2, ti: 10, ov: -37.2, p12: 76.59, p1: 56.74 },
  { t: "LMT", co: "Lockheed Martin Corp.", sec: "Industrials", ind: "Aerospace & Defense", px: 474.70, mc: 110000, tr: "Uptrend", rm: 100, ti: 1, ov: 10.3, p12: 420.00, p1: 460.00 },
  { t: "CVX", co: "Chevron Corporation", sec: "Energy", ind: "Oil & Gas Integrated", px: 155.23, mc: 280000, tr: "Uptrend", rm: 52, ti: 6, ov: 8.1, p12: 148.00, p1: 149.00 },
  { t: "ABT", co: "Abbott Laboratories", sec: "Healthcare", ind: "Medical Devices", px: 134.56, mc: 232000, tr: "Uptrend", rm: 75, ti: 4, ov: 12.8, p12: 115.00, p1: 128.00 },
  { t: "KO", co: "The Coca-Cola Company", sec: "Consumer Defensive", ind: "Beverages - Non-Alcoholic", px: 66.20, mc: 284000, tr: "Snapback", rm: 35, ti: 8, ov: 1.2, p12: 62.00, p1: 64.50 },
  { t: "MCD2", co: "Placeholder", sec: "Consumer Cyclical", ind: "Restaurants", px: 0, mc: 0, tr: "Unknown", rm: 0, ti: 10, ov: 0, p12: 0, p1: 0 },
].filter(s => s.t !== "MCD2" && s.px > 0);

// Breadth summary for header
const R3K_SUMMARY = {
  n: 49,
  up: 49.0,
  pb: 16.3,
  dn: 26.5,
  sb: 8.2,
};

// ============================================================
// SHARED COMPONENTS
// ============================================================

const font = (f) => f === "h" ? "'Fraunces', serif" : "'DM Sans', sans-serif";

const Badge = ({ score, size = "md" }) => {
  const cfg = { Positive: { bg: "#d1fae5", tx: "#065f46", bd: "#6ee7b7" }, Neutral: { bg: "#fef3c7", tx: "#92400e", bd: "#fcd34d" }, Negative: { bg: "#fecaca", tx: "#991b1b", bd: "#fca5a5" } }[score] || { bg: C.s100, tx: C.s600, bd: C.s300 };
  const sz = { sm: { p: "2px 10px", fs: "11px" }, md: { p: "4px 14px", fs: "13px" }, lg: { p: "6px 18px", fs: "15px" } }[size];
  const Icon = score === "Positive" ? TrendingUp : score === "Negative" ? TrendingDown : Minus;
  return <span style={{ ...sz, padding: sz.p, fontSize: sz.fs, background: cfg.bg, color: cfg.tx, border: `1.5px solid ${cfg.bd}`, borderRadius: "9999px", display: "inline-flex", alignItems: "center", gap: "4px", fontWeight: 700, fontFamily: font() }}><Icon size={size === "sm" ? 11 : 14} />{score}</span>;
};

const TrendBadge = ({ trend, compact }) => {
  const t = TREND_COLORS[trend];
  if (!t) return null;
  return <span style={{ background: t.bg, color: t.text, padding: compact ? "1px 8px" : "2px 10px", borderRadius: "6px", fontSize: compact ? "11px" : "12px", fontWeight: 600, fontFamily: font(), whiteSpace: "nowrap" }}>{trend}</span>;
};

const TierPill = ({ tier }) => <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "26px", height: "22px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, fontFamily: font(), background: `${TIER_COLOR(tier)}18`, color: TIER_COLOR(tier), border: `1.5px solid ${TIER_COLOR(tier)}40` }}>{tier}</span>;

const MiniBar = ({ value, max = 100, color, width = 56 }) => (
  <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
    <div style={{ width, height: "5px", borderRadius: "3px", background: C.s200 }}>
      <div style={{ width: `${Math.min(Math.max((value / max) * 100, 0), 100)}%`, height: "100%", borderRadius: "3px", background: color || C.emerald, transition: "width 0.5s" }} />
    </div>
    <span style={{ fontSize: "11px", fontWeight: 600, color: C.s700, fontFamily: font(), minWidth: "24px" }}>{value}</span>
  </div>
);

const Card = ({ children, style, onClick }) => (
  <div onClick={onClick} style={{ background: "white", borderRadius: "16px", border: `1px solid ${C.s100}`, boxShadow: "0 1px 3px rgba(0,0,0,0.05)", ...style }}>
    {children}
  </div>
);

const CardTitle = ({ children, icon, right }) => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      {icon && <span style={{ color: C.s400 }}>{icon}</span>}
      <h3 style={{ fontFamily: font("h"), fontSize: "17px", fontWeight: 700, color: C.s800, margin: 0 }}>{children}</h3>
    </div>
    {right}
  </div>
);

const MetricRow = ({ label, value, sub, color }) => (
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", fontSize: "13px", fontFamily: font() }}>
    <span style={{ color: C.s500 }}>{label}</span>
    <div style={{ textAlign: "right" }}>
      <span style={{ fontWeight: 600, color: color || C.s800 }}>{value}</span>
      {sub && <div style={{ fontSize: "10px", color: C.s400 }}>{sub}</div>}
    </div>
  </div>
);

const StatusChip = ({ label, positive }) => (
  <span style={{ fontSize: "11px", fontWeight: 700, padding: "2px 8px", borderRadius: "6px", background: positive ? "#d1fae520" : "#fecaca20", color: positive ? C.emerald : C.red, border: `1px solid ${positive ? C.emerald : C.red}30` }}>{label}</span>
);

const Spark = ({ data, w = 100, h = 28, color = C.emerald }) => {
  if (!data || data.length < 2) return null;
  const mn = Math.min(...data), mx = Math.max(...data), rng = mx - mn || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - mn) / rng) * (h - 4) - 2}`).join(" ");
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <polygon points={`0,${h} ${pts} ${w},${h}`} fill={color} fillOpacity="0.12" />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

// Health Score Gauge
const HealthGauge = ({ score, total, label, wins, misses, onClick, expanded }) => {
  const pct = score / total * 100;
  const color = pct >= 80 ? C.emerald : pct >= 60 ? C.amber : C.red;
  return (
    <div onClick={onClick} style={{ cursor: "pointer", padding: "20px 24px", background: `linear-gradient(135deg, ${C.s800}, ${C.s900})`, borderRadius: "16px", color: "white", position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: 0, right: 0, width: "200px", height: "200px", background: `radial-gradient(circle at top right, ${color}15, transparent 70%)`, pointerEvents: "none" }} />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", position: "relative" }}>
        <div>
          <div style={{ fontSize: "11px", fontWeight: 700, color: C.s400, textTransform: "uppercase", letterSpacing: "0.08em", fontFamily: font(), marginBottom: "4px" }}>
            Market Health Score
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
            <span style={{ fontFamily: font("h"), fontSize: "48px", fontWeight: 900, color }}>{score}</span>
            <span style={{ fontSize: "18px", fontWeight: 500, color: C.s400 }}>/ {total}</span>
          </div>
          <div style={{ fontFamily: font(), fontSize: "14px", fontWeight: 600, color, marginTop: "2px" }}>{label}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: "11px", color: C.s400, fontFamily: font(), marginBottom: "6px" }}>
            {wins.length} tailwinds · {misses.length} headwinds
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px", justifyContent: "flex-end", fontSize: "12px", color: C.s400 }}>
            <span>Details</span>
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </div>
        </div>
      </div>
      <div style={{ marginTop: "12px", height: "6px", borderRadius: "3px", background: "rgba(255,255,255,0.1)", overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: `linear-gradient(90deg, ${color}, ${color}cc)`, borderRadius: "3px", transition: "width 0.8s ease" }} />
      </div>
    </div>
  );
};

// Stock Detail Modal
const StockDetail = ({ s, onClose }) => {
  if (!s) return null;
  const r12 = ((s.px - s.p12) / s.p12 * 100).toFixed(1);
  const r1 = ((s.px - s.p1) / s.p1 * 100).toFixed(1);
  let sig, sigC, sigBg;
  if (s.rm >= 70 && (s.tr === "Uptrend" || s.tr === "Pullback")) { sig = "+ Strong Momentum"; sigC = "#065f46"; sigBg = "#d1fae5"; }
  else if (s.rm <= 30 && (s.tr === "Downtrend" || s.tr === "Snapback")) { sig = "− Weak Momentum"; sigC = "#991b1b"; sigBg = "#fecaca"; }
  else { sig = "○ Monitor"; sigC = "#92400e"; sigBg = "#fef3c7"; }

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(15,23,42,0.5)", backdropFilter: "blur(4px)" }}>
      <div onClick={e => e.stopPropagation()} style={{ background: "white", borderRadius: "20px", width: "min(540px, 94vw)", maxHeight: "88vh", overflow: "auto", boxShadow: "0 25px 50px rgba(0,0,0,0.15)" }}>
        <div style={{ padding: "24px 28px 18px", background: `linear-gradient(135deg, ${C.s800}, ${C.s900})`, borderRadius: "20px 20px 0 0", color: "white" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                <span style={{ fontFamily: font("h"), fontSize: "28px", fontWeight: 700 }}>{s.t}</span>
                <TrendBadge trend={s.tr} />
              </div>
              <div style={{ fontFamily: font(), fontSize: "13px", color: C.s300 }}>{s.co}</div>
              <div style={{ fontFamily: font(), fontSize: "11px", color: C.s400, marginTop: "2px" }}>{s.sec} · {s.ind}</div>
            </div>
            <button onClick={onClose} style={{ background: "rgba(255,255,255,0.1)", border: "none", borderRadius: "10px", padding: "8px", cursor: "pointer", color: "white", display: "flex" }}><X size={16} /></button>
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "10px", marginTop: "14px" }}>
            <span style={{ fontFamily: font(), fontSize: "30px", fontWeight: 700 }}>${s.px.toFixed(2)}</span>
            <span style={{ fontSize: "13px", fontWeight: 600, color: r12 >= 0 ? "#6ee7b7" : "#fca5a5" }}>{r12 > 0 ? "+" : ""}{r12}% (12m)</span>
          </div>
          <div style={{ marginTop: "10px", padding: "5px 12px", borderRadius: "8px", background: sigBg, color: sigC, fontFamily: font(), fontSize: "13px", fontWeight: 700, display: "inline-block" }}>{sig}</div>
        </div>
        <div style={{ padding: "20px 28px 24px" }}>
          {[
            { title: "Price Momentum", icon: <TrendingUp size={15} />, rows: [
              { l: "Trend Stage", v: <TrendBadge trend={s.tr} compact /> },
              { l: "Rel. Momentum Rank", v: `${s.rm}th pctl` },
              { l: "Momentum Tier", v: <TierPill tier={s.ti} /> },
              { l: "% vs 150 MA", v: <span style={{ color: s.ov >= 0 ? C.emerald : C.red, fontWeight: 600 }}>{s.ov > 0 ? "+" : ""}{s.ov}%</span> },
              { l: "12-Month Return", v: <span style={{ color: r12 >= 0 ? C.emerald : C.red, fontWeight: 600 }}>{r12 > 0 ? "+" : ""}{r12}%</span> },
              { l: "1-Month Return", v: <span style={{ color: r1 >= 0 ? C.emerald : C.red, fontWeight: 600 }}>{r1 > 0 ? "+" : ""}{r1}%</span> },
            ]},
            { title: "Company Profile", icon: <Layers size={15} />, rows: [
              { l: "Sector", v: s.sec },
              { l: "Industry", v: s.ind },
              { l: "Market Cap", v: `$${s.mc >= 1000000 ? (s.mc / 1000000).toFixed(1) + "T" : s.mc >= 1000 ? (s.mc / 1000).toFixed(0) + "B" : s.mc + "M"}` },
            ]},
          ].map((dim, di) => (
            <div key={di} style={{ marginBottom: di < 1 ? "16px" : 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px", fontFamily: font(), fontSize: "13px", fontWeight: 700, color: C.s800 }}>{dim.icon}{dim.title}</div>
              <div style={{ background: C.s50, borderRadius: "10px", padding: "10px 14px" }}>
                {dim.rows.map((r, i) => <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px", fontFamily: font(), padding: "4px 0" }}><span style={{ color: C.s500 }}>{r.l}</span><span style={{ color: C.s800 }}>{r.v}</span></div>)}
              </div>
            </div>
          ))}
          <div style={{ marginTop: "16px", padding: "8px 12px", background: "#fffbeb", borderRadius: "8px", border: "1px solid #fde68a", fontFamily: font(), fontSize: "10px", color: "#92400e", lineHeight: 1.5 }}>
            Educational analysis only — not investment advice. Past performance does not guarantee future results.
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// MAIN APP
// ============================================================

export default function MomentumScorecard() {
  const [tab, setTab] = useState("pulse");
  const [search, setSearch] = useState("");
  const [sortF, setSortF] = useState("rm");
  const [sortD, setSortD] = useState("desc");
  const [selStock, setSelStock] = useState(null);
  const [expSector, setExpSector] = useState(null);
  const [showHealth, setShowHealth] = useState(false);
  const [pulseView, setPulseView] = useState("overview");

  const filtered = useMemo(() => {
    let l = [...STOCKS];
    if (search) { const q = search.toLowerCase(); l = l.filter(s => s.t.toLowerCase().includes(q) || s.co.toLowerCase().includes(q) || s.sec.toLowerCase().includes(q)); }
    l.sort((a, b) => { const av = a[sortF], bv = b[sortF]; if (typeof av === "string") return sortD === "asc" ? av.localeCompare(bv) : bv.localeCompare(av); return sortD === "asc" ? av - bv : bv - av; });
    return l;
  }, [search, sortF, sortD]);

  const doSort = (f) => { if (sortF === f) setSortD(d => d === "asc" ? "desc" : "asc"); else { setSortF(f); setSortD("desc"); } };

  const m = MARKET;
  const yieldCurve = m.macro.tenYear - m.macro.twoYear;
  const shareholderYield = m.fundamental.buybackYield + m.fundamental.divYield;
  const currentRange = m.breadth.fwdReturns[4]; // 50-60% range

  const tabs = [{ id: "pulse", label: "Market Pulse" }, { id: "sectors", label: "Sectors" }, { id: "stocks", label: "Stock Screener" }];
  const pillarTabs = [
    { id: "overview", label: "Overview", icon: <Eye size={14} /> },
    { id: "macro", label: "Macro", icon: <DollarSign size={14} /> },
    { id: "earnings", label: "Fundamentals", icon: <BarChart3 size={14} /> },
    { id: "technical", label: "Technicals", icon: <Activity size={14} /> },
  ];

  return (
    <div style={{ fontFamily: font(), background: `linear-gradient(180deg, ${C.s50} 0%, white 500px)`, minHeight: "100vh", color: C.s800 }}>
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,500;9..144,700;9..144,900&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />

      {/* HEADER */}
      <div style={{ background: `linear-gradient(135deg, ${C.s900}, ${C.s800})`, padding: "18px 24px 14px", borderBottom: `3px solid ${C.emerald}` }}>
        <div style={{ maxWidth: "1100px", margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div style={{ width: "30px", height: "30px", borderRadius: "9px", background: `linear-gradient(135deg, ${C.emerald}, ${C.emeraldDark})`, display: "flex", alignItems: "center", justifyContent: "center" }}><Activity size={16} color="white" /></div>
                <h1 style={{ fontFamily: font("h"), fontSize: "20px", fontWeight: 700, color: "white", margin: 0 }}>Prosper <span style={{ color: C.emerald }}>Momentum</span> Scorecard</h1>
              </div>
              <div style={{ fontSize: "11px", color: C.s400, marginTop: "3px", marginLeft: "40px" }}>Watch List · {m.date} · {STOCKS.length} stocks · <span style={{ color: C.emerald }}>Live Data</span></div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "10px", fontWeight: 700, color: C.s400, textTransform: "uppercase", letterSpacing: "0.06em" }}>Health</div>
                <div style={{ fontFamily: font("h"), fontSize: "28px", fontWeight: 900, color: m.healthScore / m.healthTotal >= 0.8 ? C.emerald : C.amber, lineHeight: 1 }}>{m.healthScore}</div>
              </div>
              <Badge score={m.overallScore} size="md" />
            </div>
          </div>
          <div style={{ display: "flex", gap: "4px", marginTop: "14px", marginLeft: "40px" }}>
            {tabs.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)} style={{ fontFamily: font(), fontSize: "13px", fontWeight: tab === t.id ? 700 : 500, color: tab === t.id ? "white" : C.s400, background: tab === t.id ? "rgba(255,255,255,0.1)" : "transparent", border: "none", padding: "7px 16px", borderRadius: "8px 8px 0 0", cursor: "pointer", borderBottom: tab === t.id ? `2px solid ${C.emerald}` : "2px solid transparent" }}>{t.label}</button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "16px 16px 40px" }}>

        {/* ===================== MARKET PULSE ===================== */}
        {tab === "pulse" && (
          <div>
            <HealthGauge score={m.healthScore} total={m.healthTotal} label={m.healthLabel} wins={m.healthWins} misses={m.healthMisses} expanded={showHealth} onClick={() => setShowHealth(!showHealth)} />

            {showHealth && (
              <Card style={{ padding: "20px 24px", marginTop: "8px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                  <div>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: C.red, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>Headwinds ({m.healthMisses.length})</div>
                    {m.healthMisses.map((miss, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "6px", fontSize: "12px", color: C.s600, marginBottom: "5px" }}>
                        <span style={{ color: C.red, fontWeight: 700, flexShrink: 0 }}>−{miss.weight}</span>
                        <span>{miss.label}</span>
                        <span style={{ marginLeft: "auto", fontSize: "10px", color: C.s400, flexShrink: 0 }}>{miss.cat}</span>
                      </div>
                    ))}
                  </div>
                  <div>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: C.emerald, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>Tailwinds ({m.healthWins.length})</div>
                    {m.healthWins.map((w, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "6px", fontSize: "12px", color: C.s600, marginBottom: "5px" }}>
                        <span style={{ color: C.emerald, fontWeight: 700, flexShrink: 0 }}>+{w.weight}</span>
                        <span>{w.label}</span>
                        <span style={{ marginLeft: "auto", fontSize: "10px", color: C.s400, flexShrink: 0 }}>{w.cat}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            )}

            {/* Pillar Sub-Tabs */}
            <div style={{ display: "flex", gap: "6px", marginTop: "16px", marginBottom: "16px", flexWrap: "wrap" }}>
              {pillarTabs.map(pt => (
                <button key={pt.id} onClick={() => setPulseView(pt.id)} style={{
                  fontFamily: font(), fontSize: "12px", fontWeight: pulseView === pt.id ? 700 : 500,
                  color: pulseView === pt.id ? C.emeraldDark : C.s500,
                  background: pulseView === pt.id ? C.emeraldLight : C.s100,
                  border: `1.5px solid ${pulseView === pt.id ? C.emerald + "40" : "transparent"}`,
                  padding: "6px 14px", borderRadius: "8px", cursor: "pointer",
                  display: "flex", alignItems: "center", gap: "5px",
                }}>{pt.icon}{pt.label}</button>
              ))}
            </div>

            {/* ─── OVERVIEW SUB-TAB ─── */}
            {pulseView === "overview" && (
              <div>
                {/* 4 Indicator Cards */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: "10px", marginBottom: "16px" }}>
                  {[
                    { label: "Market Trend", score: m.trend.score, icon: <TrendingUp size={16} />, sub: `R3000 ${m.trend.r3kVs150MA} 150 MA · Slope ${m.trend.maSlope}` },
                    { label: "Market Breadth", score: m.breadth.pctAbove >= 60 ? "Positive" : "Neutral", icon: <BarChart3 size={16} />, sub: `${m.breadth.pctAbove.toFixed(1)}% above 150-day MA` },
                    { label: "Earnings", score: "Positive", icon: <Zap size={16} />, sub: `+${m.fundamental.earningsGrowth}% growth · ${m.fundamental.earningsBeat}% beat rate` },
                    { label: "Valuation", score: "Negative", icon: <AlertTriangle size={16} />, sub: `${m.fundamental.forwardPE}x fwd P/E vs ${m.fundamental.historicalPE}x avg` },
                  ].map((ind, i) => (
                    <Card key={i} style={{ padding: "14px 18px" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}><span style={{ color: C.s400 }}>{ind.icon}</span><span style={{ fontSize: "12px", fontWeight: 700, color: C.s700 }}>{ind.label}</span></div>
                        <Badge score={ind.score} size="sm" />
                      </div>
                      <div style={{ fontSize: "11px", color: C.s500, lineHeight: 1.4 }}>{ind.sub}</div>
                    </Card>
                  ))}
                </div>

                {/* Trend + Breadth side by side */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "14px", marginBottom: "16px" }}>
                  <Card style={{ padding: "20px 24px" }}>
                    <CardTitle icon={<TrendingUp size={16} />}>Market Trend</CardTitle>
                    <div style={{ display: "grid", gap: "6px" }}>
                      <MetricRow label="R3000 vs 150-day MA" value={m.trend.r3kVs150MA} />
                      <MetricRow label="150-day MA Slope" value={m.trend.maSlope} />
                      <MetricRow label="S&P 500" value={m.technical.sp500.toLocaleString()} />
                      <MetricRow label="S&P 500 4-Year MA" value={m.technical.sp500MA4yr.toLocaleString()} sub={m.technical.sp500 > m.technical.sp500MA4yr ? "Above ✓ Bullish" : "Below ✗"} color={m.technical.sp500 > m.technical.sp500MA4yr ? C.emerald : C.red} />
                      <MetricRow label="S&P 500 150-Day MA" value={m.technical.sp500MA150.toLocaleString()} sub={m.technical.sp500 > m.technical.sp500MA150 ? "Above ✓" : "Below ✗"} color={m.technical.sp500 > m.technical.sp500MA150 ? C.emerald : C.red} />
                    </div>
                    <div style={{ marginTop: "14px", padding: "10px", background: C.s50, borderRadius: "10px" }}>
                      <div style={{ fontSize: "10px", fontWeight: 700, color: C.s500, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>Trend Stage Breakdown (Watch List)</div>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "6px" }}>
                        {[
                          { label: "Uptrend", pct: R3K_SUMMARY.up, color: TREND_COLORS.Uptrend.fill },
                          { label: "Pullback", pct: R3K_SUMMARY.pb, color: TREND_COLORS.Pullback.fill },
                          { label: "Downtrend", pct: R3K_SUMMARY.dn, color: TREND_COLORS.Downtrend.fill },
                          { label: "Snapback", pct: R3K_SUMMARY.sb, color: TREND_COLORS.Snapback.fill },
                        ].map(s => (
                          <div key={s.label} style={{ textAlign: "center" }}>
                            <div style={{ fontSize: "18px", fontWeight: 700, color: s.color }}>{s.pct}%</div>
                            <div style={{ fontSize: "9px", color: C.s400 }}>{s.label}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </Card>

                  <Card style={{ padding: "20px 24px" }}>
                    <CardTitle icon={<BarChart3 size={16} />}>Market Breadth</CardTitle>
                    <div style={{ fontSize: "11px", color: C.s500, marginBottom: "8px" }}>% of stocks above their 150-day moving average</div>
                    <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginBottom: "10px" }}>
                      <span style={{ fontFamily: font("h"), fontSize: "34px", fontWeight: 700, color: C.s800 }}>{m.breadth.pctAbove.toFixed(1)}%</span>
                      <span style={{ fontSize: "11px", color: C.s500 }}>R3000 at {m.breadth.r3kPrice.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                    </div>
                    <div style={{ height: "8px", borderRadius: "4px", background: C.s200, overflow: "hidden", marginBottom: "12px" }}>
                      <div style={{ height: "100%", borderRadius: "4px", background: m.breadth.pctAbove > 60 ? C.emerald : C.amber, width: `${m.breadth.pctAbove}%`, transition: "width 0.5s" }} />
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: C.s400, marginBottom: "12px" }}>
                      <span>0%</span><span style={{ color: C.amber }}>60% threshold</span><span>100%</span>
                    </div>
                    <div style={{ padding: "8px 10px", background: "#f0fdf4", borderRadius: "8px", border: "1px solid #bbf7d0" }}>
                      <div style={{ fontSize: "10px", fontWeight: 700, color: "#065f46", marginBottom: "2px" }}>Historical Context (1995–2023)</div>
                      <div style={{ fontSize: "11px", color: "#047857", lineHeight: 1.5 }}>At {currentRange.range.toLowerCase()}, the R3000 has returned <strong>+{currentRange.fwd}%</strong> over the next 12 months on average. The market spends {currentRange.pctTime}% of the time in this range.</div>
                    </div>
                  </Card>
                </div>

                {/* Strategic Synthesis */}
                <Card style={{ padding: "20px 24px", marginBottom: "16px" }}>
                  <CardTitle icon={<Target size={16} />}>Strategic Synthesis</CardTitle>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "12px" }}>
                    {Object.entries(m.synthesis).map(([key, val]) => (
                      <div key={key} style={{ padding: "16px", background: C.s50, borderRadius: "12px", borderLeft: `4px solid ${val.color}` }}>
                        <div style={{ fontSize: "10px", fontWeight: 700, color: C.s500, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "4px" }}>{key === "fixedIncome" ? "Fixed Income" : key.charAt(0).toUpperCase() + key.slice(1)}</div>
                        <div style={{ fontFamily: font("h"), fontSize: "18px", fontWeight: 700, color: val.color, marginBottom: "6px" }}>{val.view}</div>
                        <div style={{ fontSize: "11px", color: C.s600, lineHeight: 1.5 }}>{val.desc}</div>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            )}

            {/* ─── ECONOMY SUB-TAB ─── */}
            {pulseView === "macro" && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "14px" }}>
                <Card style={{ padding: "20px 24px" }}>
                  <CardTitle icon={<Activity size={16} />}>Economic Growth</CardTitle>
                  <MetricRow label="Real GDP Growth" value={`+${m.macro.gdp.toFixed(1)}%`} sub="Strong (>2%)" color={m.macro.gdp > 2 ? C.emerald : C.red} />
                  <MetricRow label="Consumer Sentiment" value={m.macro.sentiment.toFixed(1)} sub={m.macro.sentiment > 70 ? "Confident" : "Weak (<70)"} color={m.macro.sentiment > 70 ? C.emerald : C.red} />
                  <MetricRow label="Regular Gas Price" value={`$${m.macro.gasPrice.toFixed(2)}`} />
                  <div style={{ fontSize: "11px", color: C.s500, marginTop: "10px", lineHeight: 1.5, borderTop: `1px solid ${C.s100}`, paddingTop: "10px" }}>
                    GDP above 2% signals a healthy expansion where corporate revenues can grow. Consumer sentiment at {m.macro.sentiment.toFixed(0)} is well below the 70 threshold — a key headwind to watch.
                  </div>
                </Card>

                <Card style={{ padding: "20px 24px" }}>
                  <CardTitle icon={<DollarSign size={16} />}>The Dual Mandate</CardTitle>
                  <MetricRow label="Unemployment Rate" value={`${m.macro.employment.toFixed(1)}%`} sub="Strong (<5%)" color={m.macro.employment < 5 ? C.emerald : C.red} />
                  <MetricRow label="Avg Hourly Earnings" value={`$${m.macro.wageGrowth.toFixed(2)}`} />
                  <MetricRow label="Initial Jobless Claims" value={`${(m.macro.joblessClaims / 1000).toFixed(0)}k`} sub="Low = Healthy" />
                  <div style={{ height: "1px", background: C.s100, margin: "8px 0" }} />
                  <MetricRow label="CPI Inflation" value={`${m.macro.inflation.toFixed(1)}%`} sub="Target: <3.0%" color={m.macro.inflation < 3 ? C.emerald : C.red} />
                  <div style={{ fontSize: "11px", color: C.s500, marginTop: "10px", lineHeight: 1.5, borderTop: `1px solid ${C.s100}`, paddingTop: "10px" }}>
                    The Fed's twin goals: maximum employment and stable prices. Both are on track — unemployment at {m.macro.employment}% and inflation at {m.macro.inflation}%. This gives the Fed room to continue easing rates.
                  </div>
                </Card>

                <Card style={{ padding: "20px 24px" }}>
                  <CardTitle icon={<Shield size={16} />}>Cost of Money & Policy</CardTitle>
                  <MetricRow label="Fed Funds Rate" value={`${m.macro.fedFunds.toFixed(2)}%`} />
                  <MetricRow label="10-Year Yield" value={`${m.macro.tenYear.toFixed(2)}%`} />
                  <MetricRow label="2-Year Yield" value={`${m.macro.twoYear.toFixed(2)}%`} />
                  <MetricRow label="Yield Curve (10Y − 2Y)" value={<span style={{ color: yieldCurve >= 0 ? C.emerald : C.red, fontWeight: 700 }}>{yieldCurve > 0 ? "+" : ""}{yieldCurve.toFixed(2)}%</span>} sub={yieldCurve >= 0 ? "Normal (Positive)" : "INVERTED"} />
                  <div style={{ height: "1px", background: C.s100, margin: "8px 0" }} />
                  <MetricRow label="30Y Mortgage Rate" value={`${m.macro.mortgage.toFixed(2)}%`} sub={m.macro.mortgage < 6 ? "Affordable" : "Elevated"} color={m.macro.mortgage < 6 ? C.emerald : C.red} />
                  <MetricRow label="Fiscal Policy" value={<StatusChip label={m.macro.fiscalPolicy} positive />} />
                  <MetricRow label="Monetary Policy" value={<StatusChip label={m.macro.monetaryPolicy} positive />} />
                  <div style={{ fontSize: "11px", color: C.s500, marginTop: "10px", lineHeight: 1.5, borderTop: `1px solid ${C.s100}`, paddingTop: "10px" }}>
                    A normal yield curve (+{yieldCurve.toFixed(2)}%) with easing monetary policy is supportive for risk assets. Mortgage rates above 6% remain a headwind for housing.
                  </div>
                </Card>

                <Card style={{ padding: "20px 24px" }}>
                  <CardTitle icon={<AlertTriangle size={16} />}>Credit & Risk Signals</CardTitle>
                  <MetricRow label="High Yield Spread" value={`${m.macro.hySpread.toFixed(2)}%`} sub={m.macro.hySpread < 4 ? "Calm (<4%)" : "Stress"} color={m.macro.hySpread < 4 ? C.emerald : C.red} />
                  <MetricRow label="IG Spread" value={`${m.macro.igSpread.toFixed(2)}%`} />
                  <div style={{ height: "1px", background: C.s100, margin: "10px 0" }} />
                  <MetricRow label="WTI Crude Oil" value={`$${m.macro.oil.toFixed(2)}`} />
                  <MetricRow label="US Dollar (DXY)" value={m.macro.dxy.toFixed(1)} />
                  <MetricRow label="Geopolitical Risk" value={m.macro.geopolitical} color={C.amber} />
                  <div style={{ fontSize: "11px", color: C.s500, marginTop: "10px", lineHeight: 1.5, borderTop: `1px solid ${C.s100}`, paddingTop: "10px" }}>
                    Credit spreads are the bond market's real-time stress detector. HY spread at {m.macro.hySpread.toFixed(2)}% signals calm — but tight spreads also mean risk may be underpriced.
                  </div>
                </Card>
              </div>
            )}

            {/* ─── EARNINGS SUB-TAB ─── */}
            {pulseView === "earnings" && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "14px" }}>
                <Card style={{ padding: "20px 24px" }}>
                  <CardTitle icon={<TrendingUp size={16} />}>Growth Engine</CardTitle>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
                    <div><div style={{ fontSize: "10px", color: C.s400, textTransform: "uppercase" }}>Sales Growth</div><div style={{ fontSize: "24px", fontWeight: 700 }}>+{m.fundamental.salesGrowth}%</div></div>
                    <div style={{ textAlign: "right" }}><div style={{ fontSize: "10px", color: C.s400, textTransform: "uppercase" }}>Earnings Growth</div><div style={{ fontSize: "24px", fontWeight: 700, color: C.emerald }}>+{m.fundamental.earningsGrowth}%</div></div>
                  </div>
                  <div style={{ height: "1px", background: C.s100, margin: "12px 0" }} />
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <div><div style={{ fontSize: "10px", color: C.s400 }}>Sales Beat Rate</div><div style={{ fontSize: "18px", fontWeight: 700, color: C.blue }}>{m.fundamental.salesBeat}%</div></div>
                    <div style={{ textAlign: "right" }}><div style={{ fontSize: "10px", color: C.s400 }}>Earnings Beat Rate</div><div style={{ fontSize: "18px", fontWeight: 700, color: C.emerald }}>{m.fundamental.earningsBeat}%</div></div>
                  </div>
                  <div style={{ height: "1px", background: C.s100, margin: "12px 0" }} />
                  <MetricRow label="Analyst Revisions (Up/Down)" value={<span style={{ fontWeight: 700, color: m.fundamental.revisions > 1 ? C.emerald : C.red }}>{m.fundamental.revisions}x</span>} sub={m.fundamental.revisions > 1 ? "Positive Momentum" : "Negative"} />
                  <div style={{ fontSize: "11px", color: C.s500, marginTop: "12px", lineHeight: 1.5, borderTop: `1px solid ${C.s100}`, paddingTop: "10px" }}>
                    Beat rates above 70% and rising revisions are bullish signals. Earnings growth at +{m.fundamental.earningsGrowth}% with sales at +{m.fundamental.salesGrowth}% shows expanding margins.
                  </div>
                </Card>

                <Card style={{ padding: "20px 24px" }}>
                  <CardTitle icon={<Shield size={16} />}>Quality & Profitability</CardTitle>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "8px" }}>
                    <div><div style={{ fontSize: "10px", color: C.s400, textTransform: "uppercase" }}>Net Margin</div><div style={{ fontSize: "24px", fontWeight: 700 }}>{m.fundamental.netMargin}%</div></div>
                    <StatusChip label={m.fundamental.marginTrend} positive />
                  </div>
                  <div style={{ height: "1px", background: C.s100, margin: "12px 0" }} />
                  <MetricRow label="Free Cash Flow Yield" value={`${m.fundamental.fcfYield}%`} sub="FCF / Mkt Cap" color={C.emerald} />
                  <MetricRow label="Capex Spending" value={`+${m.fundamental.capex}%`} />
                  <MetricRow label="Corporate Leverage" value={`${m.fundamental.leverage}x`} sub={m.fundamental.leverage < 2 ? "Healthy" : "Elevated"} />
                  <div style={{ height: "1px", background: C.s100, margin: "8px 0" }} />
                  <MetricRow label="Shareholder Yield" value={<span style={{ fontWeight: 700, color: C.emerald }}>{shareholderYield.toFixed(1)}%</span>} sub={`Buyback ${m.fundamental.buybackYield}% + Div ${m.fundamental.divYield}%`} />
                  <div style={{ fontSize: "11px", color: C.s500, marginTop: "12px", lineHeight: 1.5, borderTop: `1px solid ${C.s100}`, paddingTop: "10px" }}>
                    High margins indicate pricing power. FCF yield of {m.fundamental.fcfYield}% means strong cash generation. Leverage at {m.fundamental.leverage}x is healthy in any rate environment.
                  </div>
                </Card>

                <Card style={{ padding: "20px 24px" }}>
                  <CardTitle icon={<AlertTriangle size={16} />}>Valuation</CardTitle>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "8px" }}>
                    <div><div style={{ fontSize: "10px", color: C.s400, textTransform: "uppercase" }}>Fwd P/E Ratio</div><div style={{ fontSize: "28px", fontWeight: 700 }}>{m.fundamental.forwardPE}x</div><div style={{ fontSize: "10px", color: C.s400 }}>Current (12m Forward)</div></div>
                    <div style={{ textAlign: "right" }}><div style={{ fontSize: "20px", fontWeight: 700, color: C.s400 }}>{m.fundamental.historicalPE}x</div><div style={{ fontSize: "10px", color: C.s400 }}>10yr Avg</div></div>
                  </div>
                  <div style={{ height: "6px", borderRadius: "3px", background: C.s200, overflow: "hidden", marginTop: "8px" }}>
                    <div style={{ width: `${Math.min((m.fundamental.forwardPE / 30) * 100, 100)}%`, height: "100%", background: m.fundamental.forwardPE > m.fundamental.historicalPE ? C.amber : C.emerald }} />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9px", color: C.s400, marginTop: "3px" }}><span>Cheap</span><span>Expensive</span></div>
                  <div style={{ height: "1px", background: C.s100, margin: "12px 0" }} />
                  <MetricRow label="PEG Ratio" value={`${m.fundamental.pegRatio}`} sub={m.fundamental.pegRatio < 1.5 ? "Reasonable" : "Premium"} />
                  <div style={{ fontSize: "11px", color: C.s500, marginTop: "12px", lineHeight: 1.5, borderTop: `1px solid ${C.s100}`, paddingTop: "10px" }}>
                    At {m.fundamental.forwardPE}x vs. the 10-year average of {m.fundamental.historicalPE}x, markets are pricing in continued growth — leaving less room for error.
                  </div>
                </Card>
              </div>
            )}

            {/* ─── TECHNICAL SUB-TAB ─── */}
            {pulseView === "technical" && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "14px" }}>
                <Card style={{ padding: "20px 24px" }}>
                  <CardTitle icon={<TrendingUp size={16} />}>Trend Structure</CardTitle>
                  <div style={{ marginBottom: "10px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <span style={{ fontSize: "12px", color: C.s500 }}>S&P 500 vs 4-Year MA</span>
                      <StatusChip label={m.technical.sp500 > m.technical.sp500MA4yr ? "BULLISH" : "BEARISH"} positive={m.technical.sp500 > m.technical.sp500MA4yr} />
                    </div>
                    <div style={{ fontSize: "22px", fontWeight: 700 }}>{m.technical.sp500.toLocaleString()} <span style={{ fontSize: "13px", fontWeight: 500, color: C.s400 }}>/ {m.technical.sp500MA4yr.toLocaleString()}</span></div>
                    <div style={{ fontSize: "11px", color: C.emerald, marginTop: "4px" }}>+{((m.technical.sp500 / m.technical.sp500MA4yr - 1) * 100).toFixed(1)}% above long-term average</div>
                  </div>
                  <div style={{ height: "1px", background: C.s100, margin: "10px 0" }} />
                  <MetricRow label="S&P 500 vs 150d MA" value={<span>{m.technical.sp500.toLocaleString()} / {m.technical.sp500MA150.toLocaleString()}</span>} sub={m.technical.sp500 > m.technical.sp500MA150 ? "Above ✓" : "Below ✗"} />
                  <MetricRow label="R3000 vs 150d MA" value={<span>{m.breadth.r3kPrice.toLocaleString()} / {m.breadth.r3kMA150.toLocaleString()}</span>} sub={m.breadth.r3kPrice > m.breadth.r3kMA150 ? "Above ✓" : "Below ✗"} />
                  <div style={{ fontSize: "11px", color: C.s500, marginTop: "12px", lineHeight: 1.5, borderTop: `1px solid ${C.s100}`, paddingTop: "10px" }}>
                    The 4-year moving average tracks the long-term business cycle. Price above it = bull market. Both long-term and medium-term trends are positive — the trend is your friend.
                  </div>
                </Card>

                <Card style={{ padding: "20px 24px" }}>
                  <CardTitle icon={<Activity size={16} />}>Breadth & Participation</CardTitle>
                  <div style={{ marginBottom: "8px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                      <span style={{ color: C.s500 }}>Breadth (% > 150d MA)</span>
                      <span style={{ fontWeight: 700, color: m.breadth.pctAbove > 60 ? C.emerald : C.amber }}>{m.breadth.pctAbove.toFixed(1)}%</span>
                    </div>
                    <div style={{ height: "5px", borderRadius: "3px", background: C.s200 }}>
                      <div style={{ height: "100%", borderRadius: "3px", background: m.breadth.pctAbove > 60 ? C.emerald : C.amber, width: `${m.breadth.pctAbove}%` }} />
                    </div>
                  </div>
                  <div style={{ height: "1px", background: C.s100, margin: "10px 0" }} />
                  <div style={{ fontSize: "12px", fontWeight: 700, color: C.s700, marginBottom: "8px" }}>Trend Stage Mix</div>
                  {[
                    { label: "Uptrend", pct: R3K_SUMMARY.up, color: TREND_COLORS.Uptrend.fill },
                    { label: "Pullback", pct: R3K_SUMMARY.pb, color: TREND_COLORS.Pullback.fill },
                    { label: "Downtrend", pct: R3K_SUMMARY.dn, color: TREND_COLORS.Downtrend.fill },
                    { label: "Snapback", pct: R3K_SUMMARY.sb, color: TREND_COLORS.Snapback.fill },
                  ].map(s => (
                    <div key={s.label} style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      <span style={{ fontSize: "12px", color: C.s500, width: "80px" }}>{s.label}</span>
                      <div style={{ flex: 1, height: "5px", borderRadius: "3px", background: C.s200 }}>
                        <div style={{ height: "100%", borderRadius: "3px", background: s.color, width: `${s.pct}%` }} />
                      </div>
                      <span style={{ fontSize: "12px", fontWeight: 600, color: s.color, width: "40px", textAlign: "right" }}>{s.pct}%</span>
                    </div>
                  ))}
                  <div style={{ fontSize: "11px", color: C.s500, marginTop: "12px", lineHeight: 1.5, borderTop: `1px solid ${C.s100}`, paddingTop: "10px" }}>
                    Breadth below 60% means the rally is narrow — fewer stocks are participating. Watch for improvement above 60% to confirm broad-based strength.
                  </div>
                </Card>

                <Card style={{ padding: "20px 24px" }}>
                  <CardTitle icon={<Eye size={16} />}>Sentiment & Volatility</CardTitle>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", marginBottom: "12px" }}>
                    {[
                      { label: "Put/Call", value: m.technical.putCall, color: m.technical.putCall < 1 ? C.emerald : C.red },
                      { label: "VIX", value: m.technical.vix.toFixed(1), color: m.technical.vix < 20 ? C.emerald : C.red },
                      { label: "AAII Bull%", value: `${m.technical.aaii}%`, color: C.blue },
                    ].map((s, i) => (
                      <div key={i} style={{ textAlign: "center", padding: "10px", background: C.s50, borderRadius: "10px" }}>
                        <div style={{ fontSize: "9px", fontWeight: 700, color: C.s400, textTransform: "uppercase" }}>{s.label}</div>
                        <div style={{ fontSize: "20px", fontWeight: 700, color: s.color, marginTop: "2px" }}>{s.value}</div>
                      </div>
                    ))}
                  </div>
                  <div style={{ fontSize: "11px", color: C.s500, lineHeight: 1.5, borderTop: `1px solid ${C.s100}`, paddingTop: "10px" }}>
                    VIX at {m.technical.vix.toFixed(1)} is above the 20 comfort zone — markets are pricing in more uncertainty than usual. Put/Call below 1.0 means traders are still betting on upside despite the volatility.
                  </div>
                </Card>
              </div>
            )}
          </div>
        )}

        {/* ===================== SECTORS ===================== */}
        {tab === "sectors" && (
          <Card style={{ padding: "20px 24px" }}>
            <CardTitle icon={<Layers size={16} />} right={
              <div style={{ display: "flex", gap: "10px", fontSize: "10px" }}>
                {Object.entries(TREND_COLORS).map(([k, v]) => <div key={k} style={{ display: "flex", alignItems: "center", gap: "3px" }}><div style={{ width: "8px", height: "8px", borderRadius: "2px", background: v.fill }} /><span style={{ color: C.s500 }}>{k}</span></div>)}
              </div>
            }>Sector Technical Stages</CardTitle>
            <div style={{ display: "grid", gridTemplateColumns: "22px 160px 1fr 50px 50px", alignItems: "center", gap: "10px", padding: "6px 10px", marginBottom: "4px" }}>
              <span />
              <span style={{ fontSize: "10px", fontWeight: 700, color: C.s400, textTransform: "uppercase" }}>Sector</span>
              <span style={{ fontSize: "10px", fontWeight: 700, color: C.s400, textTransform: "uppercase" }}>Trend Mix</span>
              <span style={{ fontSize: "10px", fontWeight: 700, color: C.s400, textTransform: "uppercase", textAlign: "right" }}>Stocks</span>
              <span style={{ fontSize: "10px", fontWeight: 700, color: C.s400, textTransform: "uppercase", textAlign: "right" }}>Avg RM</span>
            </div>
            <div style={{ display: "grid", gap: "2px" }}>
              {SECTORS.sort((a, b) => b.up - a.up).map(sec => {
                const isExp = expSector === sec.name;
                const sStocks = STOCKS.filter(s => s.sec === sec.name).sort((a, b) => b.rm - a.rm);
                return (
                  <div key={sec.name}>
                    <div onClick={() => setExpSector(isExp ? null : sec.name)} style={{ display: "grid", gridTemplateColumns: "22px 160px 1fr 50px 50px", alignItems: "center", gap: "10px", padding: "10px", borderRadius: "8px", background: isExp ? C.s50 : "transparent", cursor: "pointer" }}>
                      {isExp ? <ChevronDown size={14} color={C.s400} /> : <ChevronRight size={14} color={C.s400} />}
                      <span style={{ fontSize: "12px", fontWeight: 600 }}>{sec.name}</span>
                      <div style={{ display: "flex", height: "18px", borderRadius: "3px", overflow: "hidden" }}>
                        {[{ p: sec.up, c: TREND_COLORS.Uptrend.fill }, { p: sec.pb, c: TREND_COLORS.Pullback.fill }, { p: sec.dn, c: TREND_COLORS.Downtrend.fill }, { p: sec.sb, c: TREND_COLORS.Snapback.fill }].map((sg, i) => <div key={i} style={{ width: `${sg.p}%`, background: sg.c }} />)}
                      </div>
                      <span style={{ fontSize: "11px", color: C.s500, textAlign: "right" }}>{sec.n}</span>
                      <span style={{ fontSize: "11px", fontWeight: 600, textAlign: "right", color: sec.rm >= 50 ? C.emerald : C.red }}>{sec.rm.toFixed(0)}</span>
                    </div>
                    {isExp && sStocks.length > 0 && (
                      <div style={{ padding: "4px 12px 10px 44px" }}>
                        {sStocks.map(s => (
                          <div key={s.t} onClick={() => setSelStock(s)} style={{ display: "flex", alignItems: "center", gap: "10px", padding: "5px 6px", borderRadius: "6px", cursor: "pointer", fontSize: "12px" }} onMouseEnter={e => e.currentTarget.style.background = C.s100} onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                            <span style={{ fontWeight: 700, width: "44px" }}>{s.t}</span>
                            <span style={{ flex: 1, color: C.s600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.co}</span>
                            <TrendBadge trend={s.tr} compact />
                            <TierPill tier={s.ti} />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        {/* ===================== STOCK SCREENER ===================== */}
        {tab === "stocks" && (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "white", borderRadius: "12px", padding: "8px 14px", boxShadow: "0 1px 3px rgba(0,0,0,0.05)", border: `1px solid ${C.s200}`, marginBottom: "10px" }}>
              <Search size={15} color={C.s400} />
              <input type="text" placeholder="Search ticker, company, or sector..." value={search} onChange={e => setSearch(e.target.value)} style={{ border: "none", outline: "none", flex: 1, fontSize: "13px", fontFamily: font(), color: C.s800, background: "transparent" }} />
              {search && <button onClick={() => setSearch("")} style={{ background: "none", border: "none", cursor: "pointer", padding: "4px", display: "flex" }}><X size={13} color={C.s400} /></button>}
            </div>
            <Card style={{ overflow: "hidden" }}>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: font(), fontSize: "12px", minWidth: "780px" }}>
                  <thead>
                    <tr style={{ background: C.s50, borderBottom: `2px solid ${C.s200}` }}>
                      {[
                        { k: "t", l: "Ticker", w: "65px", a: "left" }, { k: "co", l: "Company", w: "160px", a: "left" },
                        { k: "px", l: "Price", w: "72px" }, { k: "tr", l: "Trend", w: "85px" },
                        { k: "rm", l: "Mom Rank", w: "80px" },
                        { k: "ov", l: "% vs 150MA", w: "78px" }, { k: "r12", l: "12M Ret", w: "70px" }, { k: "r1", l: "1M Ret", w: "65px" },
                      ].map(col => (
                        <th key={col.k} onClick={() => doSort(col.k)} style={{ padding: "9px 7px", textAlign: col.a || "center", fontWeight: 700, color: C.s600, fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.04em", cursor: "pointer", whiteSpace: "nowrap", width: col.w, userSelect: "none" }}>
                          <span style={{ display: "inline-flex", alignItems: "center", gap: "2px" }}>
                            {col.l}
                            {sortF === col.k ? (sortD === "asc" ? <ArrowUp size={10} color={C.emerald} /> : <ArrowDown size={10} color={C.emerald} />) : <span style={{ color: C.s300, fontSize: "9px" }}>⇅</span>}
                          </span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map(s => {
                      const r12 = ((s.px - s.p12) / s.p12 * 100);
                      const r1 = ((s.px - s.p1) / s.p1 * 100);
                      return (
                        <tr key={s.t} onClick={() => setSelStock(s)} style={{ borderBottom: `1px solid ${C.s100}`, cursor: "pointer" }} onMouseEnter={e => e.currentTarget.style.background = C.s50} onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                          <td style={{ padding: "9px 7px", fontWeight: 700 }}>{s.t}</td>
                          <td style={{ padding: "9px 7px", color: C.s600, maxWidth: "160px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.co}</td>
                          <td style={{ padding: "9px 7px", textAlign: "center", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>${s.px.toFixed(2)}</td>
                          <td style={{ padding: "9px 7px", textAlign: "center" }}><TrendBadge trend={s.tr} compact /></td>
                          <td style={{ padding: "9px 7px" }}><MiniBar value={s.rm} color={TIER_COLOR(s.ti)} /></td>
                          <td style={{ padding: "9px 7px", textAlign: "center", fontWeight: 600, color: s.ov >= 0 ? C.emerald : C.red, fontVariantNumeric: "tabular-nums" }}>{s.ov > 0 ? "+" : ""}{s.ov.toFixed(1)}%</td>
                          <td style={{ padding: "9px 7px", textAlign: "center", fontWeight: 600, color: r12 >= 0 ? C.emerald : C.red, fontVariantNumeric: "tabular-nums" }}>{r12 > 0 ? "+" : ""}{r12.toFixed(1)}%</td>
                          <td style={{ padding: "9px 7px", textAlign: "center", fontWeight: 600, color: r1 >= 0 ? C.emerald : C.red, fontVariantNumeric: "tabular-nums" }}>{r1 > 0 ? "+" : ""}{r1.toFixed(1)}%</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div style={{ padding: "8px 14px", fontSize: "10px", color: C.s400, borderTop: `1px solid ${C.s100}` }}>
                {filtered.length} of {STOCKS.length} stocks · Live data from Python pipeline · Click any row for details
              </div>
            </Card>
          </div>
        )}

        {/* Disclaimer */}
        <div style={{ marginTop: "20px", padding: "10px 14px", background: C.s50, borderRadius: "8px", border: `1px solid ${C.s100}`, fontSize: "10px", color: C.s400, lineHeight: 1.5, textAlign: "center" }}>
          <strong style={{ color: C.s500 }}>Prosper Momentum Scorecard</strong> — Educational analysis tool. Not investment advice. Past performance does not guarantee future results. Data sourced from Yahoo Finance and FRED. Consult a qualified financial professional before making investment decisions.
        </div>
      </div>

      {selStock && <StockDetail s={selStock} onClose={() => setSelStock(null)} />}
    </div>
  );
}
