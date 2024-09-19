import pandas as pd
import numpy as np
from scipy import stats
import csv
from datetime import datetime, timedelta

# Variables
SPREAD = 0.0002  # 0.02% spread
INITIAL_ACCOUNT_VALUE = 100000
MARGIN_PERCENTAGE = 0.5  # 50% margin
STRATEGY_ALLOCATION = 1.0  # 100% of account allocated to strategy
KELLY_FRACTION = 0.5  # Half Kelly criterion

def exponential_regression(x, y):
    """Calculate exponential regression."""
    y = np.log(y)
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    return slope, intercept, std_err

def calculate_regression_channels(data, day):
    """Calculate regression channels for a given day."""
    x = np.arange(day)
    y = data['close'].iloc[:day].values
    slope, intercept, std_err = exponential_regression(x, y)
    center = np.exp(slope * x + intercept)
    upper = np.exp(slope * x + intercept + std_err)
    lower = np.exp(slope * x + intercept - std_err)
    return center[-1], upper[-1], lower[-1]

def half_kelly_criterion(avg_profit, avg_loss, win_ratio):
    """Calculate half Kelly criterion."""
    full_kelly = ((avg_profit / avg_loss) * win_ratio - (1 - win_ratio)) / (avg_profit / avg_loss)
    return max(0, min(KELLY_FRACTION * full_kelly, 1))  # Ensure result is between 0 and 1

def backtest(file_path):
    # Load data
    data = pd.read_csv(file_path, parse_dates=['date'])
    data = data.sort_values('date')

    # Initialize variables
    position = 0
    account_value = INITIAL_ACCOUNT_VALUE
    trades = []
    daily_values = []
    profits = []
    losses = []

    for i in range(100, len(data)):
        date = data['date'].iloc[i]
        open_price = data['open'].iloc[i]
        high_price = data['high'].iloc[i]
        low_price = data['low'].iloc[i]
        close_price = data['close'].iloc[i]
        prev_close = data['close'].iloc[i-1]

        center, upper, lower = calculate_regression_channels(data, i)
        lower_half = (center + lower) / 2
        upper_half = (center + upper) / 2

        # Buy conditions
        if position == 0:
            if open_price > lower_half and prev_close < upper_half:
                buy_price = open_price
            elif high_price > lower_half and open_price < lower_half:
                buy_price = lower_half
            else:
                buy_price = None

            if buy_price:
                shares = int((account_value * STRATEGY_ALLOCATION * (1 + MARGIN_PERCENTAGE)) / buy_price)
                cost = shares * buy_price * (1 + SPREAD)
                account_value -= cost
                position = shares
                trades.append(('buy', date, buy_price, shares, account_value))

        # Sell conditions
        elif position > 0:
            if open_price > upper or (high_price > upper and open_price < upper):
                sell_price = min(open_price, upper)
                revenue = position * sell_price * (1 - SPREAD)
                profit = revenue - (position * buy_price)
                account_value += revenue
                if profit > 0:
                    profits.append(profit)
                else:
                    losses.append(profit)
                trades.append(('sell', date, sell_price, position, account_value))
                position = 0

        daily_values.append((date, account_value, STRATEGY_ALLOCATION))

        # Update Kelly criterion after 3 years
        if i > 3 * 252 and len(profits) > 0 and len(losses) > 0:
            avg_profit = np.mean(profits)
            avg_loss = abs(np.mean(losses))
            win_ratio = len(profits) / (len(profits) + len(losses))
            STRATEGY_ALLOCATION = half_kelly_criterion(avg_profit, avg_loss, win_ratio)

    # Calculate performance metrics
    returns = np.diff([v[1] for v in daily_values]) / [v[1] for v in daily_values][:-1]
    sharpe_ratio = np.sqrt(252) * np.mean(returns) / np.std(returns)
    sortino_ratio = np.sqrt(252) * np.mean(returns) / np.std([r for r in returns if r < 0])
    max_drawdown = np.min([v[1] for v in daily_values]) / np.maximum.accumulate([v[1] for v in daily_values]) - 1
    win_loss_ratio = len(profits) / (len(losses) if len(losses) > 0 else 1)

    # Write results to CSV files
    with open('backtest_results.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Account Value', 'Allocation'])
        writer.writerows(daily_values)

    with open('backtest_metrics.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Sharpe Ratio', sharpe_ratio])
        writer.writerow(['Sortino Ratio', sortino_ratio])
        writer.writerow(['Average Profit', np.mean(profits) if profits else 0])
        writer.writerow(['Average Loss', np.mean(losses) if losses else 0])
        writer.writerow(['Max Drawdown', max_drawdown])
        writer.writerow(['Win/Loss Ratio', win_loss_ratio])

    return account_value

# Usage
final_account_value = backtest('stock_data.csv')
print(f"Final account value: ${final_account_value:.2f}")