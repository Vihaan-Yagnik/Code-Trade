import pandas as pd
import mplfinance as mpf
from datetime import datetime

# Example input data: list of dicts corresponding to candles
data = [
    {
        "close": 8644.0,
        "date": "01-01-2025",
        "evening_star": False,
        "exchangecode": 1,
        "expiry": "01-01-0001 00:00:00",
        "high": 8644.0,
        "low": 8631.5,
        "oi": 0,
        "open": 8640.0,
        "openDateTime": "2025-01-01T09:23:00",
        "pattern": "evening_star",
        "symbolcode": 16669,
        "time": "09:23:00",
        "volume": 1708
    },
    {
        "close": 8644.95,
        "date": "01-01-2025",
        "evening_star": False,
        "exchangecode": 1,
        "expiry": "01-01-0001 00:00:00",
        "high": 8645.1,
        "low": 8627.0,
        "oi": 0,
        "open": 8645.1,
        "openDateTime": "2025-01-01T09:24:00",
        "pattern": "evening_star",
        "symbolcode": 16669,
        "time": "09:24:00",
        "volume": 2096
    },
    {
        "close": 8627.3,
        "date": "01-01-2025",
        "evening_star": True,
        "exchangecode": 1,
        "expiry": "01-01-0001 00:00:00",
        "high": 8644.7,
        "low": 8617.4,
        "oi": 0,
        "open": 8644.7,
        "openDateTime": "2025-01-01T09:25:00",
        "pattern": "evening_star",
        "symbolcode": 16669,
        "time": "09:25:00",
        "volume": 4485
    }
]

# Convert to DataFrame
df = pd.DataFrame(data)

# Convert 'openDateTime' to datetime and set as index
df['openDateTime'] = pd.to_datetime(df['openDateTime'])
df.set_index('openDateTime', inplace=True)

# Prepare DataFrame in format required by mplfinance
# Columns required: Open, High, Low, Close, Volume
df_mpf = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})

# Highlight indices where evening_star==True, e.g. with red markers on the candlestick
evening_star_indices = df_mpf.index[df_mpf['evening_star'] == True]

# Create additional 'markers' to highlight evening star candles
# We'll create a scatter plot of red dots above the high price of those candles

highlight_vals = df_mpf.apply(lambda row: row['High'] * 1.001 if row['evening_star'] else None, axis=1)
apdict = mpf.make_addplot(
    highlight_vals,
    type='scatter',
    markersize=100,
    marker='v',
    color='red'
)


# Plot candlestick with highlight
mpf.plot(
    df_mpf,
    type='candle',
    style='charles',
    addplot=apdict,
    title='Candlestick Visualization with Evening Star Highlight',
    ylabel='Price',
    volume=True
)
