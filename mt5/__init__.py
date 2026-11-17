"""MT5 integration package for Forex AI trading."""

from .connector import MT5Connector, connect, shutdown

__all__ = ["MT5Connector", "connect", "shutdown"]
