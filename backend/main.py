from flask import Flask, request, abort, render_template
import pandas as pd
import os
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS

BASE_PATH = './5Scripts'

def get_csv_files_for_date_range(stock, start_date, end_date):
    folder_path = os.path.join(BASE_PATH, stock)
    if not os.path.isdir(folder_path):
        return None
    csv_files = []
    current_date = start_date
    while current_date <= end_date:
        filename = current_date.strftime('%d-%m-%Y') + '.csv'
        full_path = os.path.join(folder_path, filename)
        if os.path.exists(full_path):
            csv_files.append(full_path)
        current_date += timedelta(days=1)
    return csv_files

def read_and_combine_csvs(file_list):
    dfs = []
    for file in file_list:
        df = pd.read_csv(file)
        dfs.append(df)
    if not dfs:
        return None
    combined_df = pd.concat(dfs, ignore_index=True)
    combined_df['openDateTime'] = pd.to_datetime(
        combined_df['date'] + ' ' + combined_df['time'], format='%d-%m-%Y %H:%M:%S')
    combined_df.sort_values('openDateTime', inplace=True)
    combined_df.reset_index(drop=True, inplace=True)
    return combined_df


def resample_df(df, timeframe='1m'):
    if timeframe == '1m':
        return df
    df = df.set_index('openDateTime')
    if timeframe == '5m':
        rule = '5T'
    elif timeframe == '15m':
        rule = '15T'
    else:
        return None
    ohlc_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'oi': 'last',
        'exchangecode': 'last',
        'symbolcode': 'last',
        'pattern': 'last',
        'evening_star': 'last',
        'date': 'last',
        'time': 'last',
        'expiry': 'last'
    }
    ohlc_dict = {k: v for k, v in ohlc_dict.items() if k in df.columns}
    df_resampled = df.resample(rule).apply(ohlc_dict).dropna(subset=['open','high','low','close'])
    df_resampled.reset_index(inplace=True)
    df_resampled['date'] = df_resampled['openDateTime'].dt.strftime('%d-%m-%Y')
    df_resampled['time'] = df_resampled['openDateTime'].dt.strftime('%H:%M:%S')
    # Reset pattern columns
    df_resampled['evening_star'] = False
    df_resampled['hammer'] = False
    df_resampled['dragonfly_doji'] = False
    df_resampled['three_white_soldiers'] = False
    df_resampled['rising_window'] = False
    return df_resampled


def is_bullish(candle):
    return candle['close'] > candle['open']

def is_bearish(candle):
    return candle['close'] < candle['open']

def is_hammer(candle):
    body = abs(candle['close'] - candle['open'])
    if body == 0:
        return False
    lower_shadow = (candle['open'] - candle['low']) if candle['open'] < candle['close'] else (candle['close'] - candle['low'])
    upper_shadow = candle['high'] - max(candle['open'], candle['close'])
    return (lower_shadow >= 2 * body) and (upper_shadow <= 0.1 * body)

def is_dragonfly_doji(candle):
    body = abs(candle['close'] - candle['open'])
    if body > 0.1 * (candle['high'] - candle['low']):  # body small relative to range
        return False
    upper_shadow = candle['high'] - max(candle['open'], candle['close'])
    lower_shadow = min(candle['open'], candle['close']) - candle['low']
    return (upper_shadow < body * 0.1) and (lower_shadow >= 2 * body and lower_shadow > 0)

def mark_patterns(df):
    # Initialize pattern columns
    df['evening_star'] = False
    df['hammer'] = False
    df['dragonfly_doji'] = False
    df['three_white_soldiers'] = False
    df['rising_window'] = False

    # Evening Star (3 candles)
    for i in range(len(df) - 2):
        c1, c2, c3 = df.iloc[i], df.iloc[i+1], df.iloc[i+2]
        c1_body = abs(c1['close'] - c1['open'])
        if (is_bullish(c1) and
            c2['open'] > c1['close'] and c2['close'] > c1['close'] and abs(c2['close'] - c2['open']) < 0.5 * c1_body and
            is_bearish(c3) and
            c3['close'] < (c1['open'] + c1['close']) / 2):
            df.at[df.index[i+2], 'evening_star'] = True

    # Hammer (single candle)
    for i in range(len(df)):
        if is_hammer(df.iloc[i]):
            df.at[df.index[i], 'hammer'] = True

    # Dragonfly Doji (single candle)
    for i in range(len(df)):
        if is_dragonfly_doji(df.iloc[i]):
            df.at[df.index[i], 'dragonfly_doji'] = True

    # Three White Soldiers (3 candles)
    for i in range(len(df) - 2):
        c1, c2, c3 = df.iloc[i], df.iloc[i+1], df.iloc[i+2]
        if (is_bullish(c1) and is_bullish(c2) and is_bullish(c3)):
            body1 = c1['close'] - c1['open']
            body2 = c2['close'] - c2['open']
            body3 = c3['close'] - c3['open']
            # Opens inside prev body and closes higher progressively
            cond = (
                (c2['open'] > c1['open'] and c2['open'] < c1['close']) and
                (c3['open'] > c2['open'] and c3['open'] < c2['close']) and
                (c1['close'] < c2['close'] < c3['close'])
            )
            if cond:
                df.at[df.index[i], 'three_white_soldiers'] = True
                df.at[df.index[i+1], 'three_white_soldiers'] = True
                df.at[df.index[i+2], 'three_white_soldiers'] = True

    # Rising Window (gap up)
    for i in range(1, len(df)):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        if curr['low'] > prev['high']:
            df.at[df.index[i], 'rising_window'] = True

    return df

@app.route('/', methods=['GET'])
def index():
    return render_template('form.html')

@app.route('/patterns', methods=['GET'])
def detect_patterns():
    stock = request.args.get('stock')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    timeframe = request.args.get('timeframe', '1m')
    patterns_param = request.args.get('pattern')  # e.g. "hammer", "evening_star", or "hammer,dragonfly_doji"

    if not stock or not start_date_str or not end_date_str:
        return abort(400, description="Missing required query parameters: stock, start_date, end_date (DD-MM-YYYY)")
    if timeframe not in ['1m', '5m', '15m']:
        return abort(400, description="timeframe must be one of: '1m', '5m', '15m'")

    try:
        start_date = datetime.strptime(start_date_str, '%d-%m-%Y').date()
        end_date = datetime.strptime(end_date_str, '%d-%m-%Y').date()
    except ValueError:
        return abort(400, description="Date format must be DD-MM-YYYY")
    if end_date < start_date:
        return abort(400, description="end_date must be after or equal to start_date")

    csv_files = get_csv_files_for_date_range(stock, start_date, end_date)
    if csv_files is None or len(csv_files) == 0:
        return abort(404, description=f"No data files found for stock {stock} in given date range.")

    df = read_and_combine_csvs(csv_files)
    if df is None or df.empty:
        return abort(404, description="No data found after reading CSV files.")

    df_resampled = resample_df(df, timeframe)
    if df_resampled is None:
        return abort(400, description="Error in resampling dataframe to requested timeframe.")

    df_final = mark_patterns(df_resampled)
    df_final['openDateTime_str'] = df_final['openDateTime'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Patterns supported
    all_patterns = ['evening_star', 'hammer', 'dragonfly_doji', 'three_white_soldiers', 'rising_window']

    # Process pattern filter param
    if patterns_param:
        requested_patterns = [p.strip().lower() for p in patterns_param.split(',')]
        invalid_patterns = [p for p in requested_patterns if p not in all_patterns]
        if invalid_patterns:
            return abort(400, description=f"Invalid pattern(s) requested: {', '.join(invalid_patterns)}")
        # Remove columns of patterns NOT requested, to simplify template rendering
        for p in all_patterns:
            if p not in requested_patterns:
                if p in df_final.columns:
                    df_final.drop(p, axis=1, inplace=True)
    else:
        requested_patterns = all_patterns  # Show all patterns if none specified

    return render_template('chart_table.html',  # reuse existing template
                           stock=stock,
                           start_date=start_date_str,
                           end_date=end_date_str,
                           timeframe=timeframe,
                           requested_patterns=requested_patterns,
                           tables=df_final.to_dict(orient='records'))


if __name__ == "__main__":
    app.run(debug=True)
