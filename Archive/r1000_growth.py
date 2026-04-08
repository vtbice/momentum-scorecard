import requests
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import time
from tqdm import tqdm

# === SETTINGS FOR THIS FILE (R1000 Growth) ===
INDEX_NAME = "R1000 Growth"
ETF_TICKER = "IWF"

# Dates for 6 months
end_date = datetime.now().date()
start_date = end_date - timedelta(days=183)

print(f"Analyzing {INDEX_NAME} for period: {start_date} to {end_date}")

# iShares holdings URL for IWF
url = "https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf/1467271812596.ajax?fileType=csv&fileName=IWF_holdings&dataType=fund"

# Fetch holdings
response = requests.get(url)
if response.status_code == 200:
    from io import StringIO
    df = pd.read_csv(StringIO(response.text), skiprows=9)
    df = df[df['Asset Class'] == 'Equity']
    df['Weight (%)'] = pd.to_numeric(df['Weight (%)'], errors='coerce')
    weights = dict(zip(df['Ticker'], df['Weight (%)']))
    tickers = df['Ticker'].dropna().unique().tolist()
    print(f"Found {len(tickers)} stocks in {INDEX_NAME}")
else:
    print(f"Error fetching holdings: {response.status_code}")
    exit()

# Get return function
def get_return(ticker):
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if not data.empty and len(data) > 1:
            start_price = float(data['Close'].iloc[0])
            end_price = float(data['Close'].iloc[-1])
            return (end_price - start_price) / start_price * 100
    except Exception as e:
        print(f"Error for {ticker}: {e}")
    return None

# Get index return
index_ret = get_return(ETF_TICKER)
print(f"{INDEX_NAME} 6-month return: {index_ret:.2f}%" if index_ret is not None else f"{INDEX_NAME}: N/A (rate limit or no data)")

# Process stocks (limited to 200 for testing; remove [:200] for full)
outperformers = []
for ticker in tqdm(tickers[:200], desc=f"{INDEX_NAME} stocks", unit="stock"):
    ret = get_return(ticker)
    time.sleep(10)  # Delay to avoid rate limit
    if ret is not None and (index_ret is None or ret > index_ret):
        weight = weights.get(ticker, 0.00)
        try:
            info = yf.Ticker(ticker).info
            sector = info.get('sector', 'N/A')
            industry = info.get('industry', 'N/A')
            mcap = info.get('marketCap', 'N/A')
            price = info.get('currentPrice', 'N/A')
        except:
            sector = industry = mcap = price = 'N/A'
        
        outperformers.append({
            'Ticker': ticker,
            'Return (%)': round(ret, 2),
            'Weight (%)': round(weight, 2),
            'GICS Sector': sector,
            'Industry': industry,
            'Market Cap': mcap,
            'Current Price': price
        })

if outperformers:
    df = pd.DataFrame(outperformers)
    df = df.sort_values('Return (%)', ascending=False)
    filename = "r1000_growth_outperformers.csv"
    df.to_csv(filename, index=False)
    print(f"\nDone! Saved {len(outperformers)} outperformers to {filename}")
    print("Open in Excel to see index return (printed above) and all columns.")
    print("Top 20:")
    print(df.head(20).to_string(index=False))
else:
    print("No outperformers found or data issue (likely rate limit). Wait 30–60 min and retry.")