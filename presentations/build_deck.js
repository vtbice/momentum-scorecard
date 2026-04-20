// Momentum Scorecard — Market Pulse Overview deck (automated)
// Dynamic values come from env vars (see build_deck.py) with sensible fallbacks.
const pptx = require("pptxgenjs");
const env = process.env;

const L = {
  todayStr:            env.DECK_DATE           || "April 20, 2026",
  spPrice:             env.DECK_SP             || "7,126",
  healthScore:         env.DECK_HEALTH         || "86",
  healthLabel:         env.DECK_LABEL          || "Cautiously Bullish",
  view:                env.DECK_VIEW           || "Bullish",
  tailwindCount:       env.DECK_TW_COUNT       || "19",
  headwindCount:       env.DECK_HW_COUNT       || "3",
  tailwindLines:       JSON.parse(env.DECK_TW_LINES || '["Labor 4.4% · GDP 2.9% · Inflation 2.7%","Trend positive (above 150-day + 4-year MA)","VIX 19 · HY OAS 3.15% · MOVE 66","Yield curve +0.51% · ISM 50 · IPO ETF risk-on"]'),
  headwindLines:       JSON.parse(env.DECK_HW_LINES || '["Mortgage rates 6.65% (want below 6%)","Trailing P/E 28x (want below 22x)","Breadth 53% (want above 60% or below 20%)"]'),
  trendStatus:         env.DECK_TREND          || "Positive",
  ma150:               env.DECK_MA150          || "6,786",
  ma4yr:               env.DECK_MA4YR          || "5,180",
  ma150Pct:            env.DECK_MA150_PCT      || "+5.0%",
  ma4yrPct:            env.DECK_MA4YR_PCT      || "+37.6%",
  cyclicalGain:        env.DECK_CYC_GAIN       || "99",
  extension:           env.DECK_EXT            || "+5.0%",
  extensionZone:       env.DECK_EXT_ZONE       || "Healthy Uptrend",
  extensionBucketTime: env.DECK_EXT_TIME       || "24.8%",
  extensionBucketFwd:  env.DECK_EXT_FWD        || "+9.9%",
  extensionCurrentIdx: parseInt(env.DECK_EXT_IDX || "5", 10),
  breadthPct:          env.DECK_BREADTH        || "53",
  breadthZone:         env.DECK_BR_ZONE        || "Narrow",
  breadthBucketFwd:    env.DECK_BR_FWD         || "+7%",
  breadthCurrentIdx:   parseInt(env.DECK_BR_IDX || "5", 10),
  bull3Years:          env.DECK_BULL3_YRS      || "~10 yrs so far",
  bull3Gain:           env.DECK_BULL3_GAIN     || "+195% so far",
  roomToRun:           env.DECK_ROOM_TO_RUN    || "~11 years",
  pullbackTotal:       env.DECK_PB_TOTAL       || "62",
  outputPath:          env.DECK_OUTPUT         || "/tmp/momentum_deck/Market_Pulse_Overview.pptx"
};

const p = new pptx();
p.layout = "LAYOUT_WIDE";
p.author = "Vernon Bice";
p.title  = "Momentum Scorecard — Market Pulse";
p.company = "Prosper Momentum";

const C = {
  navy: "0F172A", slate: "1E293B", slateSoft: "334155",
  cream: "F8FAFC", mist: "E2E8F0", silver: "CBD5E1", mute: "94A3B8", muteDark: "64748B",
  emerald: "10B981", emeraldDeep: "059669", green: "22C55E",
  amber: "F59E0B", amberDeep: "92400E", orange: "F97316", red: "EF4444",
  white: "FFFFFF"
};
const F = { head: "Georgia", body: "Calibri" };

const TOTAL = 10;

function dark(s)  { s.background = { color: C.navy }; }
function light(s) { s.background = { color: C.cream }; }

function footer(s, n, total) {
  s.addText("Momentum Scorecard · Market Pulse",
    { x: 0.5, y: 7.05, w: 7, h: 0.3, fontSize: 10, color: C.mute, fontFace: F.body });
  s.addText(`${n} / ${total}`,
    { x: 12, y: 7.05, w: 0.8, h: 0.3, fontSize: 10, color: C.mute, fontFace: F.body, align: "right" });
}

function accentBar(s, x, y, w, color = C.emerald) {
  s.addShape(p.shapes.RECTANGLE, { x, y, w, h: 0.08, fill: { color }, line: { color, width: 0 } });
}

function eyebrow(s, text, x = 0.5, y = 0.7, color = C.emerald) {
  s.addText(text, {
    x, y, w: 10, h: 0.3, fontSize: 11, fontFace: F.body,
    color, bold: true, charSpacing: 4
  });
}

function bigStat(s, x, y, w, valueText, labelText, valueColor = C.emerald) {
  s.addText(valueText, {
    x, y, w, h: 1.1, fontSize: 54, fontFace: F.head, color: valueColor, bold: true, margin: 0
  });
  s.addText(labelText, {
    x, y: y + 1.05, w, h: 0.4, fontSize: 12, fontFace: F.body,
    color: C.muteDark, charSpacing: 2, bold: true, margin: 0
  });
}

// ── Bar chart rendered with shapes (precise positioning + YOU ARE HERE marker) ──
function drawBarChart(slide, opts) {
  // opts: {x, y, w, h, labels, values, barColors, maxVal, currentIdx, caption, pillColor}
  const n = opts.labels.length;
  const yAxisW = 0.45;
  const xAxisH = 0.32;
  const captionH = opts.caption ? 0.3 : 0;
  const valueGapH = 0.22;
  const pillH = 0.24;
  const pillPad = 0.05;

  const hasCur = opts.currentIdx !== undefined && opts.currentIdx >= 0;
  const topRegionH = hasCur ? (pillH + pillPad) : 0;

  const barRegionX = opts.x + yAxisW;
  const barRegionW = opts.w - yAxisW;
  const barRegionY = opts.y + topRegionH + valueGapH;
  const barRegionH = opts.h - topRegionH - valueGapH - xAxisH - captionH;

  const barGap = 0.14;
  const barW = (barRegionW - barGap * (n - 1)) / n;
  const baselineY = barRegionY + barRegionH;

  // Light horizontal gridlines (at 1/4 intervals)
  for (let i = 1; i <= 4; i++) {
    const yy = barRegionY + barRegionH * (1 - i / 4);
    slide.addShape(p.shapes.LINE, {
      x: barRegionX, y: yy, w: barRegionW, h: 0,
      line: { color: "EEF2F7", width: 0.5 }
    });
  }
  // Baseline
  slide.addShape(p.shapes.LINE, {
    x: barRegionX, y: baselineY, w: barRegionW, h: 0,
    line: { color: "CBD5E1", width: 0.75 }
  });

  // Y-axis labels (0, 50%, 100% of max)
  [0, opts.maxVal * 0.5, opts.maxVal].forEach(t => {
    const yt = barRegionY + barRegionH * (1 - t / opts.maxVal);
    slide.addText(Math.round(t) + "%", {
      x: opts.x, y: yt - 0.09, w: yAxisW - 0.05, h: 0.2,
      fontSize: 8, color: "A3B2C2", align: "right", valign: "middle", fontFace: F.body, margin: 0
    });
  });

  // Bars
  opts.values.forEach((v, i) => {
    const bh = (v / opts.maxVal) * barRegionH;
    const bx = barRegionX + i * (barW + barGap);
    const by = baselineY - bh;
    const color = opts.barColors[i];

    slide.addShape(p.shapes.RECTANGLE, {
      x: bx, y: by, w: barW, h: bh,
      fill: { color }, line: { color, width: 0 }
    });

    // Value label
    slide.addText(Math.round(v) + "%", {
      x: bx - 0.05, y: by - valueGapH, w: barW + 0.1, h: valueGapH,
      fontSize: 10, color: color, bold: true,
      align: "center", valign: "bottom", fontFace: F.body, margin: 0
    });

    // X-axis label
    const isCur = i === opts.currentIdx;
    slide.addText(opts.labels[i], {
      x: bx - 0.05, y: baselineY + 0.04, w: barW + 0.1, h: xAxisH - 0.04,
      fontSize: 8, color: isCur ? C.navy : C.muteDark,
      bold: isCur, align: "center", valign: "top", fontFace: F.body, margin: 0
    });
  });

  // YOU ARE HERE pill + connector
  if (hasCur) {
    const curBarX = barRegionX + opts.currentIdx * (barW + barGap);
    const curBarCenter = curBarX + barW / 2;
    const pillW = 1.25;
    const minX = opts.x + yAxisW;
    const maxX = opts.x + opts.w - pillW;
    const pillX = Math.max(minX, Math.min(curBarCenter - pillW / 2, maxX));
    const pillColor = opts.pillColor || C.emerald;

    slide.addShape(p.shapes.ROUNDED_RECTANGLE, {
      x: pillX, y: opts.y, w: pillW, h: pillH,
      fill: { color: pillColor }, line: { color: pillColor, width: 0 }, rectRadius: 0.12
    });
    slide.addText("YOU ARE HERE", {
      x: pillX, y: opts.y, w: pillW, h: pillH,
      fontSize: 8, color: C.white, bold: true, align: "center", valign: "middle", charSpacing: 2, margin: 0, fontFace: F.body
    });

    // Dashed connector line
    const curBh = (opts.values[opts.currentIdx] / opts.maxVal) * barRegionH;
    const curBarY = baselineY - curBh;
    const lineTopY = opts.y + pillH;
    const lineBotY = curBarY - valueGapH;
    slide.addShape(p.shapes.LINE, {
      x: curBarCenter, y: lineTopY, w: 0, h: Math.max(0.05, lineBotY - lineTopY),
      line: { color: pillColor, width: 1, dashType: "dash" }
    });
  }

  // Caption (chart X-axis title)
  if (opts.caption) {
    slide.addText(opts.caption, {
      x: barRegionX, y: baselineY + xAxisH + 0.04, w: barRegionW, h: captionH - 0.04,
      fontSize: 9, color: C.muteDark, bold: true, align: "center", fontFace: F.body, margin: 0
    });
  }
}

// ══════════════════════════════════════════════════════════
// SLIDE 1 — Cover
// ══════════════════════════════════════════════════════════
{
  const s = p.addSlide(); dark(s);
  s.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: 0.25, h: 7.5, fill: { color: C.emerald }, line: { width: 0 } });

  s.addText("MOMENTUM SCORECARD", {
    x: 0.9, y: 1.3, w: 10, h: 0.4, fontSize: 14, fontFace: F.body,
    color: C.emerald, bold: true, charSpacing: 6
  });
  s.addText("Market Pulse", {
    x: 0.9, y: 1.8, w: 12, h: 1.4, fontSize: 72, fontFace: F.head, color: C.white, bold: true, margin: 0
  });
  s.addText("Direction · Conviction · Participation", {
    x: 0.9, y: 3.2, w: 12, h: 0.7, fontSize: 24, fontFace: F.body, color: C.silver, italic: true, margin: 0
  });

  const sy = 5.4;
  s.addText("S&P 500", { x: 0.9, y: sy, w: 3, h: 0.3, fontSize: 10, color: C.mute, bold: true, charSpacing: 3 });
  s.addText(L.spPrice,   { x: 0.9, y: sy+0.3, w: 3, h: 0.7, fontSize: 36, color: C.white, fontFace: F.head, bold: true, margin: 0 });
  s.addText("HEALTH SCORE", { x: 4.4, y: sy, w: 3, h: 0.3, fontSize: 10, color: C.mute, bold: true, charSpacing: 3 });
  s.addText(L.healthScore + " / 100",     { x: 4.4, y: sy+0.3, w: 3, h: 0.7, fontSize: 36, color: C.emerald, fontFace: F.head, bold: true, margin: 0 });
  s.addText("VIEW", { x: 7.9, y: sy, w: 4, h: 0.3, fontSize: 10, color: C.mute, bold: true, charSpacing: 3 });
  s.addText(L.view, { x: 7.9, y: sy+0.3, w: 4, h: 0.7, fontSize: 36, color: C.white, fontFace: F.head, bold: true, margin: 0 });

  s.addText(L.todayStr, { x: 0.9, y: 6.9, w: 12, h: 0.4, fontSize: 11, color: C.mute, fontFace: F.body, charSpacing: 3 });
}

// ══════════════════════════════════════════════════════════
// SLIDE 2 — Health Score (with curated tailwinds)
// ══════════════════════════════════════════════════════════
{
  const s = p.addSlide(); light(s);
  accentBar(s, 0.5, 0.5, 1.2);
  eyebrow(s, "HEALTH SCORE");
  s.addText(L.healthLabel, {
    x: 0.5, y: 1.05, w: 12, h: 0.9, fontSize: 40, fontFace: F.head, color: C.navy, bold: true, margin: 0
  });

  // Left — big score card
  s.addShape(p.shapes.RECTANGLE, {
    x: 0.5, y: 2.1, w: 5.6, h: 4.5,
    fill: { color: C.white }, line: { color: C.mist, width: 1 },
    shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.08 }
  });
  s.addText(L.healthScore, {
    x: 0.5, y: 2.5, w: 5.6, h: 2.7, fontSize: 200, fontFace: F.head,
    color: C.emerald, bold: true, align: "center", valign: "middle", margin: 0
  });
  s.addText("out of 100", {
    x: 0.5, y: 5.3, w: 5.6, h: 0.45, fontSize: 16, fontFace: F.body,
    color: C.muteDark, align: "center", italic: true
  });
  s.addText(L.tailwindCount + " TAILWINDS  ·  " + L.headwindCount + " HEADWINDS", {
    x: 0.5, y: 5.95, w: 5.6, h: 0.4, fontSize: 12, color: C.slateSoft, align: "center", bold: true, charSpacing: 3
  });

  // Right — Tailwinds / Headwinds at-a-glance (macro, trend, risk, and sentiment groups)
  s.addShape(p.shapes.RECTANGLE, {
    x: 6.4, y: 2.1, w: 6.4, h: 2.15,
    fill: { color: "F0FDF4" }, line: { width: 0 }
  });
  s.addShape(p.shapes.RECTANGLE, { x: 6.4, y: 2.1, w: 0.1, h: 2.15, fill: { color: C.emerald }, line: { width: 0 } });
  s.addText(L.tailwindCount + " TAILWINDS", { x: 6.7, y: 2.2, w: 6, h: 0.4, fontSize: 13, bold: true, color: C.emeraldDeep, charSpacing: 3 });
  const twRich = L.tailwindLines.map((t, i) => ({
    text: t, options: i < L.tailwindLines.length - 1 ? { breakLine: true } : {}
  }));
  s.addText(twRich, { x: 6.7, y: 2.65, w: 6, h: 1.55, fontSize: 13, color: C.slateSoft, fontFace: F.body, valign: "top" });

  s.addShape(p.shapes.RECTANGLE, {
    x: 6.4, y: 4.45, w: 6.4, h: 2.15,
    fill: { color: "FEF2F2" }, line: { width: 0 }
  });
  s.addShape(p.shapes.RECTANGLE, { x: 6.4, y: 4.45, w: 0.1, h: 2.15, fill: { color: C.red }, line: { width: 0 } });
  s.addText(L.headwindCount + " HEADWINDS", { x: 6.7, y: 4.55, w: 6, h: 0.4, fontSize: 13, bold: true, color: C.red, charSpacing: 3 });
  const hwRich = L.headwindLines.map((t, i) => ({
    text: t, options: i < L.headwindLines.length - 1 ? { breakLine: true } : {}
  }));
  s.addText(hwRich, { x: 6.7, y: 5.0, w: 6, h: 1.55, fontSize: 13, color: C.slateSoft, fontFace: F.body, valign: "top" });

  footer(s, 2, TOTAL);
}

// ══════════════════════════════════════════════════════════
// SLIDE 3 — Three-Layer Framework
// ══════════════════════════════════════════════════════════
{
  const s = p.addSlide(); dark(s);
  s.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: 0.25, h: 7.5, fill: { color: C.emerald }, line: { width: 0 } });

  s.addText("THE FRAMEWORK", { x: 0.9, y: 0.7, w: 10, h: 0.3, fontSize: 12, color: C.emerald, bold: true, charSpacing: 5 });
  s.addText("Three Layers of Market Health", {
    x: 0.9, y: 1.05, w: 12, h: 0.9, fontSize: 40, fontFace: F.head, color: C.white, bold: true, margin: 0
  });
  s.addText("Each layer answers a different question — together they triangulate where the market really stands.", {
    x: 0.9, y: 2.0, w: 12, h: 0.6, fontSize: 15, color: C.silver, italic: true
  });

  const cards = [
    { label: "DIRECTION",    head: "Market Trend",   body: "Which way is the market moving — above or below its moving averages?", icon: "→" },
    { label: "CONVICTION",   head: "Trend Strength", body: "How far extended is the trend? Deep oversold and strong uptrends both pay.", icon: "↑" },
    { label: "PARTICIPATION",head: "Market Breadth", body: "How many stocks are along for the ride? Broad rallies are more durable.", icon: "▦" }
  ];
  const xs = [0.9, 5.25, 9.6], cw = 3.55, ch = 3.8, cy = 2.95;
  cards.forEach((c, i) => {
    s.addShape(p.shapes.RECTANGLE, { x: xs[i], y: cy, w: cw, h: ch, fill: { color: C.slate }, line: { color: "2F3E54", width: 1 } });
    s.addShape(p.shapes.RECTANGLE, { x: xs[i], y: cy, w: cw, h: 0.08, fill: { color: C.emerald }, line: { width: 0 } });
    s.addText(c.icon, { x: xs[i]+0.3, y: cy+0.35, w: 1, h: 1, fontSize: 54, fontFace: F.head, color: C.emerald, bold: true, margin: 0 });
    s.addText(c.label, { x: xs[i]+0.3, y: cy+1.45, w: cw-0.6, h: 0.3, fontSize: 11, color: C.emerald, bold: true, charSpacing: 4 });
    s.addText(c.head, { x: xs[i]+0.3, y: cy+1.75, w: cw-0.6, h: 0.6, fontSize: 24, fontFace: F.head, color: C.white, bold: true, margin: 0 });
    s.addText(c.body, { x: xs[i]+0.3, y: cy+2.45, w: cw-0.6, h: 1.2, fontSize: 13, color: C.silver, fontFace: F.body, valign: "top" });
  });

  footer(s, 3, TOTAL);
}

// ══════════════════════════════════════════════════════════
// SLIDE 4 — Market Trend (DIRECTION)
// ══════════════════════════════════════════════════════════
{
  const s = p.addSlide(); light(s);
  accentBar(s, 0.5, 0.5, 1.2);
  eyebrow(s, "LAYER 1 · DIRECTION");
  s.addText("Market Trend", {
    x: 0.5, y: 1.05, w: 12, h: 0.9, fontSize: 40, fontFace: F.head, color: C.navy, bold: true, margin: 0
  });
  s.addText("The S&P 500 sits above both its 4-year moving average and its 150-day moving average — long-term and intermediate trends are aligned up.", {
    x: 0.5, y: 2.0, w: 12.3, h: 0.7, fontSize: 15, color: C.slateSoft, italic: true
  });

  // Left — status card with S&P and both MAs
  s.addShape(p.shapes.RECTANGLE, {
    x: 0.5, y: 2.9, w: 5.9, h: 3.7,
    fill: { color: C.white }, line: { color: C.mist, width: 1 },
    shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.08 }
  });
  bigStat(s, 0.9, 3.15, 5.1, L.trendStatus, "CURRENT TREND READING", C.emerald);

  // Three-row MA comparison
  const mrows = [
    { label: "S&P 500",       value: L.spPrice, extra: "" },
    { label: "4-year MA",     value: L.ma4yr,   extra: "(" + L.ma4yrPct + ")" },
    { label: "150-day MA",    value: L.ma150,   extra: "(" + L.ma150Pct + ")" }
  ];
  const my0 = 4.8, myStep = 0.55;
  mrows.forEach((r, i) => {
    const y = my0 + i * myStep;
    s.addText(r.label, {
      x: 0.9, y, w: 2.4, h: 0.5, fontSize: 13, color: C.muteDark, bold: true, charSpacing: 2, valign: "middle", margin: 0
    });
    s.addText(r.value, {
      x: 3.2, y, w: 1.6, h: 0.5, fontSize: 20, color: C.navy, bold: true, fontFace: F.head, align: "right", valign: "middle", margin: 0
    });
    if (r.extra) {
      s.addText(r.extra, {
        x: 4.85, y, w: 1.3, h: 0.5, fontSize: 13, color: C.emerald, bold: true, fontFace: F.body, valign: "middle", margin: 0
      });
    }
  });

  // Right — what it means (4yr MA first)
  s.addShape(p.shapes.RECTANGLE, { x: 6.7, y: 2.9, w: 6.1, h: 3.7, fill: { color: "F0FDF4" }, line: { width: 0 } });
  s.addShape(p.shapes.RECTANGLE, { x: 6.7, y: 2.9, w: 0.1, h: 3.7, fill: { color: C.emerald }, line: { width: 0 } });
  s.addText("WHAT IT MEANS", { x: 7.0, y: 3.05, w: 6, h: 0.3, fontSize: 11, bold: true, color: C.emeraldDeep, charSpacing: 3 });
  s.addText([
    { text: "Above 4-year MA (" + L.ma4yrPct + ")  →  long-term secular trend intact", options: { bullet: true, breakLine: true } },
    { text: "Above 150-day MA (" + L.ma150Pct + ")  →  intermediate trend is up",        options: { bullet: true, breakLine: true } },
    { text: "Both moving averages are themselves sloping up — the trend is gaining ground, not just drifting above its averages.", options: { bullet: true, breakLine: true } },
    { text: "The current cyclical bull started October 2022 at S&P 3,577 (+" + L.cyclicalGain + "% since)." }
  ], { x: 7.0, y: 3.45, w: 5.8, h: 3.1, fontSize: 13, color: C.slateSoft, fontFace: F.body, valign: "top" });

  footer(s, 4, TOTAL);
}

// ══════════════════════════════════════════════════════════
// SLIDE 5 — Trend Strength (CONVICTION) — J-curve
// ══════════════════════════════════════════════════════════
{
  const s = p.addSlide(); light(s);
  accentBar(s, 0.5, 0.5, 1.2, C.green);
  eyebrow(s, "LAYER 2 · CONVICTION", 0.5, 0.7, C.green);
  s.addText("Trend Strength", {
    x: 0.5, y: 1.05, w: 12, h: 0.9, fontSize: 40, fontFace: F.head, color: C.navy, bold: true, margin: 0
  });
  s.addText("How far the S&P sits from its 150-day MA — and why extended trends tend to keep winning.", {
    x: 0.5, y: 2.0, w: 12.3, h: 0.5, fontSize: 15, color: C.slateSoft, italic: true
  });

  // Left — current reading
  s.addShape(p.shapes.RECTANGLE, {
    x: 0.5, y: 2.75, w: 4.1, h: 3.75,
    fill: { color: C.white }, line: { color: C.mist, width: 1 },
    shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.08 }
  });
  bigStat(s, 0.8, 3.0, 3.5, L.extension, "S&P 500 VS 150-DAY MA", C.green);
  s.addText("Zone: " + L.extensionZone, { x: 0.8, y: 4.55, w: 3.5, h: 0.4, fontSize: 14, color: C.green, bold: true });
  s.addText(L.extensionBucketTime + " of trading days since 1957 have sat in this bucket.",
    { x: 0.8, y: 4.95, w: 3.5, h: 0.7, fontSize: 12, color: C.muteDark });
  s.addText("AVG 1-YR FWD RETURN", { x: 0.8, y: 5.65, w: 3.5, h: 0.3, fontSize: 10, color: C.muteDark, bold: true, charSpacing: 2 });
  s.addText(L.extensionBucketFwd, { x: 0.8, y: 5.9, w: 3.5, h: 0.55, fontSize: 30, color: C.green, bold: true, fontFace: F.head, margin: 0 });

  // Right — chart card
  s.addShape(p.shapes.RECTANGLE, {
    x: 4.9, y: 2.75, w: 7.9, h: 3.75,
    fill: { color: C.white }, line: { color: C.mist, width: 1 },
    shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.08 }
  });
  s.addText("THE J-CURVE · 1-YEAR FORWARD RETURNS (1957–2025)", {
    x: 5.15, y: 2.88, w: 7.4, h: 0.3, fontSize: 10, bold: true, color: C.navy, charSpacing: 3
  });

  const jLabels = ["<-15%","-15 to -10","-10 to -5","-5 to 0","0 to +5","+5 to +10","+10 to +15","+15 to +20",">+20%"];
  const jValues = [24.7, 16.4, 8.7, 6.7, 7.6, 9.9, 10.0, 12.6, 16.4];
  const jColors = jValues.map(v =>
    v >= 15 ? C.emerald : v >= 10 ? C.green : v >= 7 ? C.amber : C.orange
  );
  drawBarChart(s, {
    x: 5.15, y: 3.25, w: 7.4, h: 3.05,
    labels: jLabels, values: jValues, barColors: jColors,
    maxVal: 28, currentIdx: L.extensionCurrentIdx,
    caption: "S&P 500 Extension vs 150-day MA  —  Low to High",
    pillColor: C.green
  });

  // Insight line (safely below card, above footer)
  s.addText("Key finding: extended trends keep winning. Deep-oversold (<-15%) pays +24.7%, the slightly-below zone is weakest (+6.7%), and +15-20% extended still returns +12.6%.", {
    x: 0.5, y: 6.6, w: 12.3, h: 0.4, fontSize: 12, color: C.slateSoft, italic: true, fontFace: F.body
  });

  footer(s, 5, TOTAL);
}

// ══════════════════════════════════════════════════════════
// SLIDE 6 — Market Breadth (PARTICIPATION) — U-shape
// ══════════════════════════════════════════════════════════
{
  const s = p.addSlide(); light(s);
  accentBar(s, 0.5, 0.5, 1.2, C.amber);
  eyebrow(s, "LAYER 3 · PARTICIPATION", 0.5, 0.7, C.amber);
  s.addText("Market Breadth", {
    x: 0.5, y: 1.05, w: 12, h: 0.9, fontSize: 40, fontFace: F.head, color: C.navy, bold: true, margin: 0
  });
  s.addText("What percentage of stocks are trading above their 150-day MA — the 'are we all in this together' signal.", {
    x: 0.5, y: 2.0, w: 12.3, h: 0.5, fontSize: 15, color: C.slateSoft, italic: true
  });

  // Left — current reading
  s.addShape(p.shapes.RECTANGLE, {
    x: 0.5, y: 2.75, w: 4.1, h: 3.75,
    fill: { color: C.white }, line: { color: C.mist, width: 1 },
    shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.08 }
  });
  bigStat(s, 0.8, 3.0, 3.5, L.breadthPct + "%", "STOCKS ABOVE 150-DAY MA", C.amber);
  s.addText("Zone: " + L.breadthZone, { x: 0.8, y: 4.55, w: 3.5, h: 0.4, fontSize: 14, color: C.amber, bold: true });
  s.addText("Middling — not broad enough to signal a strong rally, but not washed out either.",
    { x: 0.8, y: 4.95, w: 3.5, h: 0.7, fontSize: 12, color: C.muteDark });
  s.addText("AVG 1-YR FWD RETURN", { x: 0.8, y: 5.65, w: 3.5, h: 0.3, fontSize: 10, color: C.muteDark, bold: true, charSpacing: 2 });
  s.addText(L.breadthBucketFwd, { x: 0.8, y: 5.9, w: 3.5, h: 0.55, fontSize: 30, color: C.amber, bold: true, fontFace: F.head, margin: 0 });

  // Right — chart card
  s.addShape(p.shapes.RECTANGLE, {
    x: 4.9, y: 2.75, w: 7.9, h: 3.75,
    fill: { color: C.white }, line: { color: C.mist, width: 1 },
    shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.08 }
  });
  s.addText("THE U-SHAPE · 1-YEAR FORWARD RETURNS (Russell 3000, 1995–2023)", {
    x: 5.15, y: 2.88, w: 7.4, h: 0.3, fontSize: 10, bold: true, color: C.navy, charSpacing: 3
  });

  const bLabels = ["<10%","10-20","20-30","30-40","40-50","50-60","60-70","70-80","80-90",">90%"];
  const bValues = [44, 22, 10, 6, 7, 7, 13, 14, 13, 11];
  const bColors = bValues.map(v =>
    v >= 15 ? C.emerald : v >= 10 ? C.green : v >= 7 ? C.amber : C.orange
  );
  drawBarChart(s, {
    x: 5.15, y: 3.25, w: 7.4, h: 3.05,
    labels: bLabels, values: bValues, barColors: bColors,
    maxVal: 50, currentIdx: L.breadthCurrentIdx,
    caption: "% of Stocks Above Their 150-day MA  —  Low to High",
    pillColor: C.amber
  });

  s.addText("Key finding: both extremes pay — washed-out capitulation (<20%) and broad participation (>60%). The middle delivers muted returns.", {
    x: 0.5, y: 6.6, w: 12.3, h: 0.4, fontSize: 12, color: C.slateSoft, italic: true, fontFace: F.body
  });

  footer(s, 6, TOTAL);
}

// ══════════════════════════════════════════════════════════
// SLIDE 7 — Where We Are Now (cyclical + secular context)
// ══════════════════════════════════════════════════════════
{
  const s = p.addSlide(); light(s);
  accentBar(s, 0.5, 0.5, 1.2);
  eyebrow(s, "WHERE WE ARE NOW");
  s.addText("Cyclical Bull, Secular Bull #3", {
    x: 0.5, y: 1.05, w: 12, h: 0.9, fontSize: 40, fontFace: F.head, color: C.navy, bold: true, margin: 0
  });
  s.addText("We are ~3.5 years into a cyclical bull market that started October 2022 — nested inside the third post-WWII secular bull that began in 2016.", {
    x: 0.5, y: 2.0, w: 12.3, h: 0.7, fontSize: 15, color: C.slateSoft, italic: true
  });

  // Three secular-bull cards
  const bulls = [
    { yrs: "1942–1966", gain: "+1,200%+",     label: "SECULAR BULL #1" },
    { yrs: "1982–2000", gain: "+1,397%",      label: "SECULAR BULL #2" },
    { yrs: "2016–?",    gain: L.bull3Gain, label: "SECULAR BULL #3 (active)" }
  ];
  const bx = [0.5, 4.75, 9.0], bw = 3.8, by = 2.95, bh = 2.0;
  bulls.forEach((b, i) => {
    const active = i === 2;
    s.addShape(p.shapes.RECTANGLE, {
      x: bx[i], y: by, w: bw, h: bh,
      fill: { color: active ? "F0FDF4" : C.white },
      line: { color: active ? C.emerald : C.mist, width: active ? 2 : 1 },
      shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.08 }
    });
    s.addText(b.label, { x: bx[i]+0.25, y: by+0.2, w: bw-0.5, h: 0.3, fontSize: 10, color: active ? C.emeraldDeep : C.muteDark, bold: true, charSpacing: 3 });
    s.addText(b.yrs,    { x: bx[i]+0.25, y: by+0.55, w: bw-0.5, h: 0.5, fontSize: 22, fontFace: F.head, color: C.navy, bold: true, margin: 0 });
    s.addText(b.gain,   { x: bx[i]+0.25, y: by+1.15, w: bw-0.5, h: 0.6, fontSize: 28, fontFace: F.head, color: active ? C.emerald : C.slateSoft, bold: true, margin: 0 });
  });

  // Projections box
  s.addShape(p.shapes.RECTANGLE, { x: 0.5, y: 5.25, w: 12.3, h: 1.55, fill: { color: C.navy }, line: { width: 0 } });
  s.addText("PROJECTIONS IF THIS BULL FOLLOWS PRIOR SECULAR PATHS", {
    x: 0.75, y: 5.4, w: 11.8, h: 0.3, fontSize: 10, color: C.emerald, bold: true, charSpacing: 3
  });
  s.addText([
    { text: "Low case (post-1966 grind): ",  options: { bold: true, color: C.silver } },
    { text: "S&P ~9,500 by 2032",            options: { color: C.white, breakLine: true } },
    { text: "Base case (1942–1966 path): ",  options: { bold: true, color: C.silver } },
    { text: "S&P ~14,000 by 2035",           options: { color: C.white, breakLine: true } },
    { text: "High case (1982–2000 path): ",  options: { bold: true, color: C.silver } },
    { text: "S&P ~27,000 by 2037 (+1,397% total)", options: { color: C.white } }
  ], { x: 0.75, y: 5.75, w: 11.8, h: 1.0, fontSize: 14, fontFace: F.body, valign: "top", margin: 0 });

  footer(s, 7, TOTAL);
}

// ══════════════════════════════════════════════════════════
// SLIDE 8 — Pullbacks Are Normal
// ══════════════════════════════════════════════════════════
{
  const s = p.addSlide(); light(s);
  accentBar(s, 0.5, 0.5, 1.2);
  eyebrow(s, "HISTORICAL CONTEXT");
  s.addText("Pullbacks Are Normal", {
    x: 0.5, y: 1.05, w: 12, h: 0.9, fontSize: 40, fontFace: F.head, color: C.navy, bold: true, margin: 0
  });
  s.addText("Since 1957, the S&P has grown from 44 to " + L.spPrice + " — stumbling " + L.pullbackTotal + " times along the way and coming back every single time.", {
    x: 0.5, y: 2.0, w: 12.3, h: 0.5, fontSize: 15, color: C.slateSoft, italic: true
  });

  // 4 stat tiles
  const tiles = [
    { big: L.pullbackTotal, small: "5%+ pullbacks since 1957",  color: C.emerald },
    { big: "-8.5%",    small: "median decline",            color: "3B82F6" },
    { big: "31 days",  small: "median duration",           color: "3B82F6" },
    { big: "18%",      small: "reach -20% (bear market)",  color: C.red }
  ];
  const tx = [0.5, 3.7, 6.9, 10.1], tw = 2.8, ty = 2.8, th = 1.5;
  tiles.forEach((t, i) => {
    s.addShape(p.shapes.RECTANGLE, {
      x: tx[i], y: ty, w: tw, h: th,
      fill: { color: C.white }, line: { color: C.mist, width: 1 },
      shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.08 }
    });
    s.addText(t.big, {
      x: tx[i], y: ty + 0.15, w: tw, h: 0.8, fontSize: 36, fontFace: F.head,
      color: t.color, bold: true, align: "center", valign: "middle", margin: 0
    });
    s.addText(t.small, {
      x: tx[i] + 0.15, y: ty + 1.0, w: tw - 0.3, h: 0.4, fontSize: 12,
      color: C.slateSoft, align: "center", bold: true
    });
  });

  // Severity table
  s.addText("NOT EVERY SLIP IS THE SAME", {
    x: 0.5, y: 4.5, w: 12, h: 0.3, fontSize: 11, bold: true, color: C.navy, charSpacing: 3
  });
  const rows = [
    ["Severity",      "Decline",   "Share",           "What It Feels Like"],
    ["Routine",       "5–10%",     "63% of pullbacks", "A stumble on the trail — over before most notice"],
    ["Meaningful",    "10–15%",    "12%",              "You feel it — headlines get louder, but it passes"],
    ["Beyond Normal", "15–20%",    "7%",               "Real fear — but technically not a bear market"],
    ["Bear Market",   "20%+",      "18%",              "Deep valley — painful, but historically temporary"]
  ];
  const colX = [0.5, 2.4, 4.0, 6.0], colW = [1.9, 1.6, 2.0, 6.8];
  const rowH = 0.38;
  rows.forEach((r, i) => {
    const y = 4.85 + i * rowH;
    if (i === 0) {
      s.addShape(p.shapes.RECTANGLE, { x: 0.5, y, w: 12.3, h: rowH, fill: { color: C.navy }, line: { width: 0 } });
    } else if (i % 2 === 0) {
      s.addShape(p.shapes.RECTANGLE, { x: 0.5, y, w: 12.3, h: rowH, fill: { color: "F1F5F9" }, line: { width: 0 } });
    }
    const colors = [C.emerald, C.amber, C.orange, C.red];
    r.forEach((cell, j) => {
      const isHeader = i === 0;
      const severityColor = (!isHeader && j === 0) ? colors[i - 1] : (isHeader ? C.white : C.slateSoft);
      s.addText(cell, {
        x: colX[j] + 0.1, y, w: colW[j] - 0.1, h: rowH,
        fontSize: isHeader ? 10 : 11, color: severityColor,
        bold: isHeader || j === 0, charSpacing: isHeader ? 2 : 0, valign: "middle", fontFace: F.body, margin: 0
      });
    });
  });

  footer(s, 8, TOTAL);
}

// ══════════════════════════════════════════════════════════
// SLIDE 9 — Room to Run (secular cycles)
// ══════════════════════════════════════════════════════════
{
  const s = p.addSlide(); light(s);
  accentBar(s, 0.5, 0.5, 1.2);
  eyebrow(s, "SECULAR CYCLES · THE BIG PICTURE");
  s.addText("How Much Runway Is Left?", {
    x: 0.5, y: 1.05, w: 12, h: 0.9, fontSize: 40, fontFace: F.head, color: C.navy, bold: true, margin: 0
  });
  s.addText("Secular cycles run in 15–25 year regimes. The two prior secular bulls each lasted roughly 21 years — we are about halfway through the current one.", {
    x: 0.5, y: 2.0, w: 12.3, h: 0.7, fontSize: 15, color: C.slateSoft, italic: true
  });

  // Cycles table
  const cycleRows = [
    ["Cycle",                         "Years",       "Duration",        "Nominal Move"],
    ["Secular Bull #1",               "1942–1966",   "24 years",        "+1,200%+"],
    ["Secular Bear #1",               "1966–1982",   "16 years",        "Sideways grind"],
    ["Secular Bull #2",               "1982–2000",   "18 years",        "+1,397%"],
    ["Secular Bear #2",               "2000–2016",   "16 years",        "Sideways grind"],
    ["Secular Bull #3 (active)",      "2016–?",      L.bull3Years,  L.bull3Gain]
  ];
  const colX = [0.5, 4.0, 6.5, 9.0], colW = [3.5, 2.5, 2.5, 3.8];
  const rowH = 0.42;
  const tableY = 2.85;

  cycleRows.forEach((r, i) => {
    const y = tableY + i * rowH;
    const isHeader = i === 0;
    const isActive = i === 5;

    if (isHeader) {
      s.addShape(p.shapes.RECTANGLE, { x: 0.5, y, w: 12.3, h: rowH, fill: { color: C.navy }, line: { width: 0 } });
    } else if (isActive) {
      s.addShape(p.shapes.RECTANGLE, { x: 0.5, y, w: 12.3, h: rowH, fill: { color: "F0FDF4" }, line: { width: 0 } });
      s.addShape(p.shapes.RECTANGLE, { x: 0.5, y, w: 0.08, h: rowH, fill: { color: C.emerald }, line: { width: 0 } });
    } else if (i % 2 === 0) {
      s.addShape(p.shapes.RECTANGLE, { x: 0.5, y, w: 12.3, h: rowH, fill: { color: "F1F5F9" }, line: { width: 0 } });
    }

    r.forEach((cell, j) => {
      let cellColor;
      if (isHeader) cellColor = C.white;
      else if (isActive) cellColor = C.emeraldDeep;
      else if (j === 0 && r[0].startsWith("Secular Bull")) cellColor = C.emerald;
      else if (j === 0 && r[0].startsWith("Secular Bear")) cellColor = C.red;
      else cellColor = C.slateSoft;

      s.addText(cell, {
        x: colX[j] + 0.1, y, w: colW[j] - 0.1, h: rowH,
        fontSize: isHeader ? 10 : 12,
        color: cellColor,
        bold: isHeader || isActive || j === 0,
        charSpacing: isHeader ? 2 : 0,
        valign: "middle", fontFace: F.body, margin: 0
      });
    });
  });

  // Punchline banner
  const bannerY = 5.7;
  s.addShape(p.shapes.RECTANGLE, {
    x: 0.5, y: bannerY, w: 12.3, h: 1.2,
    fill: { color: C.navy }, line: { width: 0 }
  });
  s.addShape(p.shapes.RECTANGLE, {
    x: 0.5, y: bannerY, w: 12.3, h: 0.08,
    fill: { color: C.emerald }, line: { width: 0 }
  });

  s.addText("THE PUNCHLINE", {
    x: 0.75, y: bannerY + 0.15, w: 5, h: 0.3, fontSize: 11, color: C.emerald, bold: true, charSpacing: 4
  });
  s.addText(L.roomToRun, {
    x: 0.75, y: bannerY + 0.45, w: 5, h: 0.75, fontSize: 44, fontFace: F.head,
    color: C.emerald, bold: true, margin: 0, valign: "top"
  });

  s.addText([
    { text: "of secular-bull tailwind on the historical median.", options: { breakLine: true, bold: true, color: C.white } },
    { text: " ", options: { breakLine: true } },
    { text: "Bull #1 ran 24 years. Bull #2 ran 18 years. We're " + L.bull3Years + " into Bull #3 — roughly halfway through the historical cycle.", options: { color: C.silver } }
  ], {
    x: 5.5, y: bannerY + 0.2, w: 7.5, h: 1.0, fontSize: 13, fontFace: F.body, valign: "top", margin: 0
  });

  footer(s, 9, TOTAL);
}

// ══════════════════════════════════════════════════════════
// SLIDE 10 — Closing
// ══════════════════════════════════════════════════════════
{
  const s = p.addSlide(); dark(s);
  s.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: 0.25, h: 7.5, fill: { color: C.emerald }, line: { width: 0 } });

  s.addText("BOTTOM LINE", { x: 0.9, y: 0.9, w: 10, h: 0.4, fontSize: 14, color: C.emerald, bold: true, charSpacing: 5 });
  s.addText("The Setup Today", {
    x: 0.9, y: 1.4, w: 12, h: 1.0, fontSize: 48, fontFace: F.head, color: C.white, bold: true, margin: 0
  });

  const points = [
    { title: "Trend is up",                body: "S&P above both 150-day (" + L.ma150Pct + ") and 4-year (" + L.ma4yrPct + ") MAs. Long-term secular bull intact." },
    { title: "Trend strength is healthy",  body: "Extension sits in the " + L.extensionZone.toLowerCase() + " zone — historically " + L.extensionBucketFwd + " avg 1-yr fwd return." },
    { title: "Breadth is the hold-back",   body: "Only " + L.breadthPct + "% of stocks above their 150-day MA. Need >60% for a stronger signal." }
  ];
  const py = 3.0, pspace = 1.2;
  points.forEach((pt, i) => {
    const y = py + i * pspace;
    s.addShape(p.shapes.OVAL, { x: 0.9, y: y + 0.1, w: 0.55, h: 0.55, fill: { color: C.emerald }, line: { width: 0 } });
    s.addText(`${i+1}`, { x: 0.9, y: y+0.1, w: 0.55, h: 0.55, fontSize: 22, fontFace: F.head, color: C.navy, bold: true, align: "center", valign: "middle", margin: 0 });
    s.addText(pt.title, { x: 1.7, y, w: 11, h: 0.45, fontSize: 22, fontFace: F.head, color: C.white, bold: true, margin: 0 });
    s.addText(pt.body,  { x: 1.7, y: y+0.48, w: 11, h: 0.7, fontSize: 14, color: C.silver, fontFace: F.body });
  });
}

p.writeFile({ fileName: L.outputPath })
  .then(fn => console.log("Wrote", fn));
