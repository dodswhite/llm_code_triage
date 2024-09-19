#claude sonnet 3.5
import pandas as pd
import numpy as np
import mplfinance as mpf
from scipy.signal import find_peaks
from sklearn.linear_model import LinearRegression

def load_data(file_path):
    df = pd.read_csv(file_path, parse_dates=['date_time'])
    df.set_index('date_time', inplace=True)
    return df

def find_support_resistance(data, window=20, prominence=0.5):
    highs = data['high'].rolling(window=window, center=True).max()
    lows = data['low'].rolling(window=window, center=True).min()
    
    high_peaks, _ = find_peaks(highs, prominence=prominence)
    low_peaks, _ = find_peaks(-lows, prominence=prominence)
    
    return high_peaks, low_peaks

def calculate_line_strength(data, line_index, window=10):
    touches = sum((data['low'].iloc[max(0, line_index-window):line_index+window] >= data['low'].iloc[line_index]) &
                  (data['low'].iloc[max(0, line_index-window):line_index+window] <= data['low'].iloc[line_index] + 0.01 * data['low'].iloc[line_index]))
    return touches

def find_trend_channels(data, window=20):
    x = np.arange(len(data)).reshape(-1, 1)
    y_high = data['high'].values.reshape(-1, 1)
    y_low = data['low'].values.reshape(-1, 1)
    
    reg_high = LinearRegression().fit(x, y_high)
    reg_low = LinearRegression().fit(x, y_low)
    
    channel_high = reg_high.predict(x)
    channel_low = reg_low.predict(x)
    
    return channel_high, channel_low

def plot_stock_analysis(data, support_levels, resistance_levels, channel_high, channel_low):
    apds = []
    
    for level in support_levels:
        apds.append(mpf.make_addplot(pd.Series([data['low'].iloc[level]] * len(data), index=data.index),
                                     type='line', color='g', alpha=0.7, linewidth=1))
    
    for level in resistance_levels:
        apds.append(mpf.make_addplot(pd.Series([data['high'].iloc[level]] * len(data), index=data.index),
                                     type='line', color='r', alpha=0.7, linewidth=1))
    
    apds.append(mpf.make_addplot(pd.Series(channel_high.flatten(), index=data.index),
                                 type='line', color='b', alpha=0.7, linewidth=1))
    apds.append(mpf.make_addplot(pd.Series(channel_low.flatten(), index=data.index),
                                 type='line', color='b', alpha=0.7, linewidth=1))
    
    mpf.plot(data, type='candle', style='yahoo', title='Stock Price Analysis',
             addplot=apds, volume=True, figsize=(20, 10))

def main(file_path):
    data = load_data(file_path)
    
    high_peaks, low_peaks = find_support_resistance(data)
    
    support_levels = sorted(low_peaks, key=lambda x: calculate_line_strength(data, x), reverse=True)[:5]
    resistance_levels = sorted(high_peaks, key=lambda x: calculate_line_strength(data, x), reverse=True)[:5]
    
    channel_high, channel_low = find_trend_channels(data)
    
    plot_stock_analysis(data, support_levels, resistance_levels, channel_high, channel_low)

if __name__ == "__main__":
    file_path = "path_to_your_csv_file.csv"
    main(file_path)