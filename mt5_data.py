"""MT5 data retrieval helpers for closed Forex candles."""

from typing import Dict, Iterable, Optional
import MetaTrader5 as mt5
import pandas as pd


TIMEFRAME_CONSTANTS = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
}


def initialize_mt5():
    """Initialize MT5 connection."""
    if not mt5.initialize():
        raise RuntimeError("Failed to initialize MT5")


def get_valid_symbol(symbol: str) -> str:
    """Resolve symbol to valid MT5 broker format."""

    symbols = mt5.symbols_get()

    if symbols is None:
        return symbol.upper()

    symbol_names = [s.name for s in symbols]

    # Exact match
    if symbol in symbol_names:
        return symbol

    # Uppercase match
    symbol_upper = symbol.upper()

    if symbol_upper in symbol_names:
        return symbol_upper

    # Case-insensitive match
    for s in symbol_names:
        if s.upper() == symbol_upper:
            return s

    # Partial match (EURUSDm, EURUSD., etc.)
    for s in symbol_names:
        if symbol_upper in s.upper():
            return s

    return symbol_upper


def get_data(
    symbol: str,
    bars: int = 100,
    timeframe: Optional[int] = None
) -> pd.DataFrame:
    """Retrieve recent closed MT5 bars for a symbol."""

    initialize_mt5()

    if timeframe is None:
        timeframe = mt5.TIMEFRAME_M15

    valid_symbol = get_valid_symbol(symbol)
    return _get_closed_data(valid_symbol, bars, timeframe)


def _get_closed_data(symbol: str, bars: int, timeframe: int) -> pd.DataFrame:
    if bars < 1:
        raise ValueError("bars must be greater than zero")

    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Unable to select MT5 symbol {symbol}")

    rates = mt5.copy_rates_from_pos(
        symbol,
        timeframe,
        0,
        bars + 1,
    )

    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No data returned for {symbol}")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(
        df["time"],
        unit="s",
        utc=True
    )
    df = df.sort_values("time").reset_index(drop=True)

    # MT5 position zero is the currently forming candle; do not analyze it.
    if len(df) <= 1:
        raise RuntimeError(f"No completed candles returned for {symbol}")
    df = df.iloc[:-1].copy()

    return df[
        ["time", "open", "high", "low", "close", "tick_volume"]
    ].tail(bars).reset_index(drop=True)


def get_multi_tf_data(
    symbol: str,
    bars: int = 1200,
    timeframes: Optional[Iterable[str]] = None,
) -> Dict[str, object]:
    """Fetch available M1-to-W1 candles, retaining legacy H1/M15 aliases.

    Individual timeframe failures are returned in ``errors`` so one unavailable
    history window does not hide usable data from the other timeframes.
    """
    initialize_mt5()
    valid_symbol = get_valid_symbol(symbol)
    requested = [tf.upper() for tf in (timeframes or TIMEFRAME_CONSTANTS)]
    unknown = sorted(set(requested).difference(TIMEFRAME_CONSTANTS))
    if unknown:
        raise ValueError(f"Unsupported timeframe(s): {', '.join(unknown)}")

    frames: Dict[str, pd.DataFrame] = {}
    errors: Dict[str, str] = {}
    for timeframe in requested:
        try:
            frames[timeframe] = _get_closed_data(
                valid_symbol, bars, TIMEFRAME_CONSTANTS[timeframe]
            )
        except RuntimeError as exc:
            errors[timeframe] = str(exc)

    if not frames:
        details = "; ".join(f"{tf}: {error}" for tf, error in errors.items())
        raise RuntimeError(f"No timeframe data available for {valid_symbol}. {details}")

    return {
        "symbol": valid_symbol,
        "frames": frames,
        "errors": errors,
        "htf": frames.get("H1"),
        "ltf": frames.get("M15"),
    }


if __name__ == "__main__":
    data = get_multi_tf_data("EURUSD")

    print("\nHTF DATA:")
    print(data["htf"].tail())

    print("\nLTF DATA:")
    print(data["ltf"].tail())