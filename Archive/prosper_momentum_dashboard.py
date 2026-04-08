# prosper_momentum_dashboard.py - Simple beginner version of Prosper Momentum Dashboard
# Run with: streamlit run prosper_momentum_dashboard.py
# Updated to fix formatting error, show all stocks by default, and add debug prints

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import numpy as np  # For NaN handling

# Your 10 test stocks (change this later to your full list if you want)
tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'GOOGL', 'META', 'AMD', 'PLTR', 'SHOP']

# Function to calculate trend using your exact methodology
def calculate_trend(prices, ticker):
    if len(prices) < 252:
        return 'Not Enough Data', 'N/A'
    
    ma = prices.rolling(150).mean()
    ma_today = ma.iloc[-1]
    ma_2mo_ago = ma.iloc[-42] if len(ma) > 42 else None
    
    if ma_2mo_ago is None:
        return 'Not Enough Data', 'N/A'
    
    is_rising = ma_today > ma_2mo_ago
    is_above = prices.iloc[-1] > ma_today
    
    # Debug print (shows in Terminal)
    print(f"DEBUG {ticker}: Price={prices.iloc[-1]:.2f}, MA150 Today={ma_today:.2f}, MA150 2mo Ago={ma_2mo_ago:.2f if ma_2mo_ago is not None else 'N/A'}, Is Rising={is_rising}, Is Above={is_above}")
    
    if is_rising and is_above:
        return 'Uptrend', 'Above rising SMA'
    elif not is_rising and is_above:
        return 'Snapback', 'Above falling SMA'
    elif is_rising and not is_above:
        return 'Pullback', 'Below rising SMA'
    else:
        return 'Downtrend', 'Below falling SMA'

# Set up the app layout
st.set_page_config(page_title="Prosper Momentum Dashboard", layout="wide")
st.title("Prosper Momentum Dashboard")
st.markdown("**Methodology**: Stocks classified by 150-day SMA. Uptrend: Above rising SMA | Snapback: Above falling SMA | Pullback: Below rising SMA | Downtrend: Below falling SMA")

# Progress bar and status
progress_bar = st.progress(0)
status_text = st.empty()

# Load data
data_rows = []
for i, ticker in enumerate(tickers):
    status_text.text(f"Loading {ticker} ({i+1}/{len(tickers)})...")
    
    try:
        end = datetime.today().strftime('%Y-%m-%d')
        start = (datetime.today() - timedelta(days=400)).strftime('%Y-%m-%d')
        prices = yf.download(ticker, start=start, end=end)['Close']
        prices.name = ticker  # For debug
        
        if len(prices) < 252:
            data_rows.append({
                'Ticker': ticker,
                'Trend': 'Not Enough Data',
                'Description': 'N/A',
                'Price': np.nan,
                'MA150 Today': np.nan,
                'MA150 2mo Ago': np.nan
            })
        else:
            trend, description = calculate_trend(prices, ticker)
            price_val = prices.iloc[-1]
            ma_today_val = prices.rolling(150).mean().iloc[-1]
            ma_2mo_val = prices.rolling(150).mean().iloc[-42] if len(prices) > 42 else np.nan
            
            data_rows.append({
                'Ticker': ticker,
                'Trend': trend,
                'Description': description,
                'Price': price_val if pd.notna(price_val) else np.nan,
                'MA150 Today': ma_today_val if pd.notna(ma_today_val) else np.nan,
                'MA150 2mo Ago': ma_2mo_val if pd.notna(ma_2mo_val) else np.nan
            })
    except Exception as e:
        print(f"Error loading {ticker}: {e}")
        data_rows.append({
            'Ticker': ticker,
            'Trend': 'Error Loading',
            'Description': 'N/A',
            'Price': np.nan,
            'MA150 Today': np.nan,
            'MA150 2mo Ago': np.nan
        })
    
    progress_bar.progress((i+1)/len(tickers))
    time.sleep(0.5)

status_text.text("Loading complete!")

df = pd.DataFrame(data_rows)

# Interactive table with safe styling (no gradient to avoid NaN issues)
st.subheader("Momentum Dashboard")
st.dataframe(
    df.style.format({
        'Price': '${:.2f}',
        'MA150 Today': '${:.2f}',
        'MA150 2mo Ago': '${:.2f}'
    }),
    use_container_width=True
)

# Filters (default to show all)
col1, col2 = st.columns(2)
with col1:
    trend_filter = st.multiselect("Show only these trends", options=df['Trend'].unique(), default=[])
with col2:
    st.write(" ")  # Placeholder for future filters

filtered_df = df[df['Trend'].isin(trend_filter)] if trend_filter else df  # Show all if no filter

st.subheader(f"Filtered Results ({len(filtered_df)} stocks)")
st.dataframe(filtered_df, use_container_width=True)

# Export button
csv = filtered_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download Filtered CSV",
    data=csv,
    file_name="prosper_momentum_filtered.csv",
    mime="text/csv"
)

st.markdown("---")
st.caption("Data from Yahoo Finance. Not financial advice. Built with Streamlit.")