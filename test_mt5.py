"""Quick MT5 connection test - run from main project directory."""

from mt5 import connect, shutdown


if __name__ == "__main__":
    if connect():
        print("\n✅ Successfully connected to MT5!")
        print("Account is ready for trading.\n")
        shutdown()
    else:
        print("❌ Failed to connect to MT5")
        print("Make sure MetaTrader 5 is running and you're logged in.")
