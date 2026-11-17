"""Example: Connect to MetaTrader 5 and retrieve account information."""

from mt5 import connect, shutdown


def main():
    """Test MT5 connection."""
    if connect():
        print("\n✅ Successfully connected to MT5!")
        print("You can now execute trades programmatically.\n")
        
        # Add your trading logic here
        # Example:
        #   - Get symbol info
        #   - Place orders
        #   - Retrieve account history
        
        shutdown()
        print("✅ MT5 connection closed")
    else:
        print("❌ Failed to connect to MT5")


if __name__ == "__main__":
    main()
