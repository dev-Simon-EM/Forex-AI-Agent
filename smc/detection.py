"""SMC detection utilities for Forex OHLC data."""

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"time", "open", "high", "low", "close"}


def standardize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize dataframe columns and enforce required OHLC fields."""
    df = df.copy()
    df.columns = [col.strip().lower() for col in df.columns]

    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {sorted(missing)}")

    df = df[list(REQUIRED_COLUMNS)].copy()
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    if df["time"].isnull().any():
        raise ValueError("Invalid time values found in OHLC data")

    return df.sort_values("time").reset_index(drop=True)


def is_swing_high(df: pd.DataFrame, index: int, window: int = 2) -> bool:
    """Return True when the candle at index is a swing high."""
    if index < window or index + window >= len(df):
        return False

    current_high = df.at[index, "high"]
    prior_highs = df.loc[index - window : index - 1, "high"]
    next_highs = df.loc[index + 1 : index + window, "high"]

    result = current_high > prior_highs.max() and current_high > next_highs.max()
    logger.debug("Swing high at %s? %s", df.at[index, "time"], result)
    return result


def is_swing_low(df: pd.DataFrame, index: int, window: int = 2) -> bool:
    """Return True when the candle at index is a swing low."""
    if index < window or index + window >= len(df):
        return False

    current_low = df.at[index, "low"]
    prior_lows = df.loc[index - window : index - 1, "low"]
    next_lows = df.loc[index + 1 : index + window, "low"]

    result = current_low < prior_lows.min() and current_low < next_lows.min()
    logger.debug("Swing low at %s? %s", df.at[index, "time"], result)
    return result


def _find_recent_swing_levels(
    df: pd.DataFrame, index: int, lookback: int = 20
) -> Tuple[Optional[float], Optional[float]]:
    """Find the most recent swing high and swing low before the current candle."""
    start = max(0, index - lookback)
    swing_high = None
    swing_low = None

    for i in range(start, index):
        if is_swing_high(df, i):
            swing_high = df.at[i, "high"]
        if is_swing_low(df, i):
            swing_low = df.at[i, "low"]

    logger.debug(
        "Recent swings before %s -> high=%s low=%s",
        df.at[index, "time"],
        swing_high,
        swing_low,
    )
    return swing_high, swing_low


def detect_market_structure(df: pd.DataFrame, index: int, window: int = 5) -> str:
    """Detect bullish/bearish/unknown market structure from recent candles."""
    if index < window:
        return "unknown"

    highs = df.loc[index - window : index - 1, "high"].tolist()
    lows = df.loc[index - window : index - 1, "low"].tolist()

    bullish = all(highs[i] <= highs[i + 1] for i in range(len(highs) - 1)) and all(
        lows[i] <= lows[i + 1] for i in range(len(lows) - 1)
    )
    bearish = all(highs[i] >= highs[i + 1] for i in range(len(highs) - 1)) and all(
        lows[i] >= lows[i + 1] for i in range(len(lows) - 1)
    )

    structure = "bullish" if bullish else "bearish" if bearish else "unknown"
    logger.debug("Structure at %s = %s", df.at[index, "time"], structure)
    return structure


def detect_bos(
    df: pd.DataFrame,
    index: int,
    prev_structure: str,
    lookback: int = 5,
) -> bool:
    """Detect Break of Structure (BOS) using recent swing levels."""
    if prev_structure == "unknown" or index < lookback:
        return False

    candle = df.loc[index]
    window = df.loc[index - lookback : index - 1]

    if prev_structure == "bullish":
        prior_high = window["high"].max()
        result = candle["close"] > prior_high and candle["open"] > prior_high
    elif prev_structure == "bearish":
        prior_low = window["low"].min()
        result = candle["close"] < prior_low and candle["open"] < prior_low
    else:
        result = False

    logger.debug("BOS at %s? %s", candle["time"], result)
    return result


def detect_choch(prev_structure: str, current_structure: str) -> bool:
    """Detect Change of Character (CHoCH) when structure flips."""
    if prev_structure == "unknown" or current_structure == "unknown":
        return False
    result = prev_structure != current_structure
    logger.debug("CHOCH from %s to %s? %s", prev_structure, current_structure, result)
    return result


def detect_liquidity_zone(
    df: pd.DataFrame,
    index: int,
    lookback: int = 10,
    tolerance: float = 0.00015,
) -> Optional[str]:
    """Detect liquidity zones by matching recent equal highs or lows."""
    if index < lookback:
        return None

    candle = df.loc[index]
    window = df.loc[index - lookback : index - 1]

    equal_highs = (window["high"].sub(candle["high"]).abs() < tolerance).sum()
    equal_lows = (window["low"].sub(candle["low"]).abs() < tolerance).sum()

    if equal_highs >= 2:
        logger.debug("Liquidity zone equal_highs at %s", candle["time"])
        return "equal_highs"
    if equal_lows >= 2:
        logger.debug("Liquidity zone equal_lows at %s", candle["time"])
        return "equal_lows"
    return None


def detect_order_block(
    df: pd.DataFrame,
    index: int,
    structure: str,
    bos: bool,
    max_lookback: int = 3,
) -> Optional[Dict[str, object]]:
    """Detect a bullish or bearish order block near the current breakout candle."""
    if not bos or structure == "unknown" or index < 1:
        return None

    for lookback in range(1, min(max_lookback, index) + 1):
        candidate = df.loc[index - lookback]
        is_bearish = candidate["close"] < candidate["open"]
        is_bullish = candidate["close"] > candidate["open"]

        if structure == "bullish" and is_bearish:
            logger.debug("Bullish order block found at %s", df.at[index - lookback, "time"])
            return {
                "type": "bullish",
                "start_time": df.at[index - lookback, "time"],
                "end_time": df.at[index - lookback, "time"],
                "high": candidate["high"],
                "low": candidate["low"],
            }

        if structure == "bearish" and is_bullish:
            logger.debug("Bearish order block found at %s", df.at[index - lookback, "time"])
            return {
                "type": "bearish",
                "start_time": df.at[index - lookback, "time"],
                "end_time": df.at[index - lookback, "time"],
                "high": candidate["high"],
                "low": candidate["low"],
            }

    return None


def generate_smc_signal_frame(
    df: pd.DataFrame,
    swing_window: int = 2,
    structure_window: int = 5,
    liquidity_lookback: int = 10,
    bos_lookback: int = 5,
) -> pd.DataFrame:
    """Generate an SMC signal dataframe from OHLC price data."""
    df = standardize_ohlc(df)
    rows: List[Dict[str, object]] = []
    prev_structure = "unknown"

    for index in range(len(df)):
        structure = detect_market_structure(df, index, window=structure_window)
        bos = detect_bos(df, index, prev_structure, lookback=bos_lookback)
        choch = detect_choch(prev_structure, structure)
        liquidity_zone = detect_liquidity_zone(df, index, lookback=liquidity_lookback)
        order_block = detect_order_block(df, index, structure, bos)

        row = {
            "time": df.at[index, "time"],
            "bias": structure,
            "bos": bos,
            "choch": choch,
            "liquidity_zone": liquidity_zone,
            "order_block": order_block,
        }
        rows.append(row)
        prev_structure = structure

    signal_df = pd.DataFrame(rows)
    signal_df["time"] = pd.to_datetime(signal_df["time"], utc=True)
    return signal_df
