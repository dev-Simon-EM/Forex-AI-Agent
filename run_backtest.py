import sys

from data_loader import load_ohlc_csv
from backtester import run_backtest


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python run_backtest.py path/to/ohlc.csv")
        print("\nExample CSV format:")
        print("time,open,high,low,close")
        print("2023-01-01 00:00:00,1.2345,1.2350,1.2340,1.2348")
        return

    csv_path = sys.argv[1]
    
    try:
        df = load_ohlc_csv(csv_path)
        print(f"\n✓ Loaded {len(df)} candles from {csv_path}")
        print(f"Date range: {df['time'].min()} to {df['time'].max()}\n")
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return

    try:
        result = run_backtest(df)
    except Exception as e:
        print(f"❌ Error during backtest: {e}")
        return

    print("=" * 50)
    print("BACKTEST RESULTS (SMC-Based Strategy)")
    print("=" * 50)
    print(result.summary())
    
    if result.total_trades > 0:
        print("\nFirst 5 trades:")
        for i, trade in enumerate(result.trades[:5], 1):
            print(
                f"\n{i}. {trade.direction.upper()} trade\n"
                f"   Entry: {trade.entry:.5f} | SL: {trade.sl:.5f} | TP: {trade.tp:.5f}\n"
                f"   Exit: {trade.outcome.upper()} | Profit: {trade.profit:.5f} | Duration: {trade.duration} candles"
            )
    else:
        print("\n⚠️  No trades generated. Check the data and signal generation.")


if __name__ == "__main__":
    main()
