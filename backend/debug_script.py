import yfinance as yf
import pandas_ta as ta
import pandas as pd

df = yf.download("AAPL", start="2023-01-01", end="2023-12-31", progress=False)
df.columns = df.columns.get_level_values(0)

df.ta.macd(fast=12, slow=26, signal=9, append=True)
df.ta.supertrend(length=10, multiplier=3, append=True)

print(df.tail(5))
