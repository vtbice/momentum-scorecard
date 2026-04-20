"""
S&P 500 Extension Study
-----------------------
For each trading day since 1957, measure how far the S&P 500 is above/below
its own 150-day moving average, then compute the average 1-year forward
return starting from that day. Group into buckets to see if there is a
signal in the extension.

This is the index-level analog to the existing breadth study (which uses
the share of stocks above their 150-day MA).
"""
import csv, statistics
from collections import defaultdict

CSV_PATH = "/Users/vernonbice/Documents/Market Study/SP500_Daily_March4_1957_Present.csv"
print(f"Loading {CSV_PATH} ...")
dates, prices = [], []
with open(CSV_PATH) as f:
    reader = csv.reader(f)
    next(reader)  # header
    for row in reader:
        if len(row) < 2 or not row[1]:
            continue
        dates.append(row[0])
        prices.append(float(row[1]))
print(f"  Got {len(prices):,} trading days: {dates[0]} → {dates[-1]}")

MA_WINDOW = 150
FWD_DAYS = 252  # ~1 trading year

# Compute rolling 150d MA
ma = [None] * len(prices)
running = 0.0
for i, p in enumerate(prices):
    running += p
    if i >= MA_WINDOW:
        running -= prices[i - MA_WINDOW]
    if i >= MA_WINDOW - 1:
        ma[i] = running / MA_WINDOW

# For each day with a valid MA and a valid forward return, compute extension
# and the 1-year forward return
BUCKETS = [
    ("< -15%", -999, -15),
    ("-15 to -10%", -15, -10),
    ("-10 to -5%", -10, -5),
    ("-5 to 0%",   -5,   0),
    ("0 to +5%",    0,   5),
    ("+5 to +10%",  5,  10),
    ("+10 to +15%", 10, 15),
    ("+15 to +20%", 15, 20),
    ("> +20%",     20, 999),
]

def bucket_for(ext):
    for name, lo, hi in BUCKETS:
        if lo <= ext < hi:
            return name
    return None

bucket_fwds = defaultdict(list)  # bucket -> list of fwd returns

for i in range(len(prices) - FWD_DAYS):
    if ma[i] is None:
        continue
    ext_pct = (prices[i] / ma[i] - 1) * 100
    bname = bucket_for(ext_pct)
    if bname is None:
        continue
    fwd = (prices[i + FWD_DAYS] / prices[i] - 1) * 100
    bucket_fwds[bname].append(fwd)

# Summary
total = sum(len(v) for v in bucket_fwds.values())
print(f"\nS&P 500 Extension Study — {dates[0]} to {dates[-FWD_DAYS-1]}")
print(f"Trading days with MA + 1y fwd available: {total:,}")
print(f"Overall avg 1yr fwd return: "
      f"{statistics.mean([x for xs in bucket_fwds.values() for x in xs]):+.2f}%\n")

# Print table
print(f"{'Extension Bucket':<14}  {'Count':>6}  {'% Time':>7}  {'Avg Fwd':>8}  {'Median':>8}  {'% Pos':>7}")
print("-" * 70)
for name, lo, hi in BUCKETS:
    arr = bucket_fwds.get(name, [])
    if not arr:
        print(f"{name:<14}  {'0':>6}  {'0.0%':>7}  {'-':>8}  {'-':>8}  {'-':>7}")
        continue
    n = len(arr)
    pct_time = 100 * n / total
    avg = statistics.mean(arr)
    med = statistics.median(arr)
    pos = 100 * sum(1 for x in arr if x > 0) / n
    print(f"{name:<14}  {n:>6,}  {pct_time:>6.1f}%  {avg:>+7.2f}%  {med:>+7.2f}%  {pos:>6.1f}%")

# Current reading
cur_price = prices[-1]
cur_ma = ma[-1]
if cur_ma:
    cur_ext = (cur_price / cur_ma - 1) * 100
    print(f"\nCurrent S&P extension vs 150d MA: {cur_ext:+.2f}% "
          f"(bucket: {bucket_for(cur_ext)})  [{dates[-1]}]")
