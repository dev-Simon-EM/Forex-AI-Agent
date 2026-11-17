"""
Example: Test backtester with different risk/reward ratios
"""

from data_loader import load_ohlc_csv
from backtester import run_backtest

df = load_ohlc_csv("sample_data.csv")

print("=" * 60)
print("TESTING DIFFERENT RISK/REWARD RATIOS")
print("=" * 60)

ratios = [1.0, 1.5, 2.0, 2.5]

for ratio in ratios:
    result = run_backtest(df, reward_ratio=ratio)
    print(f"\n📊 Reward Ratio: 1:{ratio}")
    print(f"   Trades: {result.total_trades} | Wins: {result.wins} | "
          f"Losses: {result.losses} | Win%: {result.win_rate:.1f}%")
    print(f"   Total P/L: {result.profit_loss:.5f} | Avg: {result.avg_profit:.5f}")

print("\n" + "=" * 60)
print("Note: Higher RR ratios give larger TP targets but lower win rates")
print("=" * 60)
