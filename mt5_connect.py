"""MT5 connection wrapper for the Forex AI system."""

from mt5 import connect as mt5_connect, shutdown as mt5_shutdown


def connect() -> bool:
    """Initialize and connect to MetaTrader 5."""
    return mt5_connect()


def shutdown() -> None:
    """Shutdown the MetaTrader 5 connection."""
    mt5_shutdown()
