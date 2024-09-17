import pandas as pd
import numpy as np
from scipy.stats import linregress
import math

def exponential_regression(y, x):
    log_y = np.log(y)
    slope, intercept, r_value, p_value, std_err = linregress(x, log_y)
    return np.exp(intercept), slope

def calculate_channel(stock_data, start_day):
    x = np.arange(1, start_day + 1)
    y = stock_data['close'][:start_day]
    a, b = exponential_regression(y, x)
    predicted = a * np.exp(b * x)
    residuals = stock_data['close'][:start_day] - predicted
    stdev = np.std(residuals)
    return predicted, stdev

def run_backtest(input_csv, spread=0.0002, start_value=100000, margin=0.5, percent_of_account=1.0, kelly_fraction=0.5):
    # Load stock data
    stock_data = pd.read_csv(input_csv)
    
    # Add regression lines
    stock_data['predicted'] = np.nan
    stock_data['-1_stdev'] = np.nan
    stock_data['1_stdev'] = np.nan
    
    equity = start_value
    positions = []
    account_value = []
    trades = []
    
    for i in range(100, len(stock_data)):
        predicted, stdev = calculate_channel(stock_data, i)
        
        stock_data.at[i, 'predicted'] = predicted[-1]
        stock_data.at[i, '-1_stdev'] = predicted[-1] - stdev
        stock_data.at[i, '1_stdev'] = predicted[-1] + stdev
        
        # Buying condition
        if len(positions) == 0:
            if stock_data['open'][i] > (stock_data['-1_stdev'][i] - 0.5 * stdev) and stock_data['close'][i-1] < (stock_data['predicted'][i-1] - 0.5 * stdev):
                buy_price = stock_data['open'][i]
                positions.append(buy_price)
                equity -= buy_price * (1 + spread)
                trades.append(('BUY', stock_data['date'][i], buy_price, equity))
        
        # Selling condition
        if len(positions) > 0:
            buy_price = positions[-1]
            if stock_data['open'][i] > (stock_data['1_stdev'][i]):
                sell_price = stock_data['open'][i]
                equity += sell_price * (1 - spread)
                positions.pop()
                trades.append(('SELL', stock_data['date'][i], sell_price, equity))
        
        account_value.append(equity)
    
    # Output account value
    output_data = pd.DataFrame({
        'date': stock_data['date'][100:],
        'account_value': account_value
    })
    
    # Sharpe, Sortino, and drawdown calculation
    returns = np.diff(account_value) / account_value[:-1]
    sharpe_ratio = np.mean(returns) / np.std(returns)
    sortino_ratio = np.mean(returns) / np.std(returns[returns < 0])
    max_drawdown = np.min(returns)
    
    # Write to CSV
    output_data.to_csv('backtest_results.csv', index=False)
    
    stats_data = pd.DataFrame({
        'Metric': ['Sharpe', 'Sortino', 'Max Drawdown'],
        'Value': [sharpe_ratio, sortino_ratio, max_drawdown]
    })
    stats_data.to_csv('backtest_stats.csv', index=False)
    
    return output_data, stats_data

# Example usage
run_backtest('stock_data.csv')