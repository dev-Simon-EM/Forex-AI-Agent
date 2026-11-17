"""
Smart Money Concepts (SMC) Strategy Module
"""

from typing import Dict, List

import pandas as pd

from smc.detection import (
    detect_liquidity_zone,
    generate_smc_signal_frame,
    standardize_ohlc,
)


# =========================================================
# SWING DETECTION
# =========================================================
def detect_swings(df: pd.DataFrame, window: int = 2) -> pd.DataFrame:
    min_move = 0.0005  # EURUSD ~5 pips (you can tune later)
    """
    Detect swing highs/lows using local extrema logic.
    """

    df = standardize_ohlc(df)

    swings = []

    for i in range(window, len(df) - window):

        high = df["high"].iloc[i]
        low = df["low"].iloc[i]

        prev_highs = df["high"].iloc[i - window:i]
        next_highs = df["high"].iloc[i + 1:i + window + 1]

        prev_lows = df["low"].iloc[i - window:i]
        next_lows = df["low"].iloc[i + 1:i + window + 1]

        range_high = max(prev_highs.max(), next_highs.max())
        range_low = min(prev_lows.min(), next_lows.min())

        body_strength = abs(high - low)

        is_swing_high = (
            high > prev_highs.max()
            and high > next_highs.max()
            and (high - range_low) > min_move
            and body_strength > (range_high - range_low) * 0.3
        )

        is_swing_low = (
            low < prev_lows.min()
            and low < next_lows.min()
            and (range_high - low) > min_move
            and body_strength > (range_high - range_low) * 0.3
        )
        swing_type = "none"
        price = df["close"].iloc[i]

        if is_swing_high:
            swing_type = "high"
            price = high

        elif is_swing_low:
            swing_type = "low"
            price = low

        swings.append({
            "index": i,
            "type": swing_type,
            "price": price,
            "time": df["time"].iloc[i]
        })

    return pd.DataFrame(swings)

# =========================================================
# BOS DETECTION
# =========================================================
def detect_bos_swing(
    df: pd.DataFrame,
    swings: pd.DataFrame
) -> bool:
    """
    Detect institutional Break of Structure (BOS).
    
    Requirements:
    - Candle CLOSE must break structure
    - Must break previous swing high/low
    - Requires displacement candle
    """

    if len(df) < 5:
        return False

    if swings.empty:
        return False

    valid_swings = swings[
        swings["type"] != "none"
    ]

    if len(valid_swings) < 2:
        return False

    # Current candle
    current_candle = df.iloc[-1]

    current_close = current_candle["close"]
    current_open = current_candle["open"]

    candle_body = abs(current_close - current_open)

    # Average recent candle body
    recent_bodies = abs(
        df.iloc[-6:-1]["close"] -
        df.iloc[-6:-1]["open"]
    )

    avg_body = recent_bodies.mean()

    # Displacement filter
    displacement = candle_body > (avg_body * 1.5)

    if not displacement:
        return False

    # Last swing point
    last_swing = valid_swings.iloc[-1]

    # Bullish BOS
    if (
        last_swing["type"] == "high"
        and current_close > last_swing["price"]
    ):
        return True

    # Bearish BOS
    if (
        last_swing["type"] == "low"
        and current_close < last_swing["price"]
    ):
        return True

    return False

# =========================================================
# CHOCH DETECTION
# =========================================================
def detect_choch_swing(
    df: pd.DataFrame,
    swings: pd.DataFrame,
    current_trend: str
) -> bool:

    if len(swings) < 4:
        return False

    recent_swings = swings[swings["type"] != "none"].tail(6)

    highs = recent_swings[
        recent_swings["type"] == "high"
    ]["price"].tolist()

    lows = recent_swings[
        recent_swings["type"] == "low"
    ]["price"].tolist()

    if len(highs) < 2 or len(lows) < 2:
        return False

    if current_trend == "bullish":
        return (
            highs[-1] < highs[-2]
            or lows[-1] < lows[-2]
        )

    elif current_trend == "bearish":
        return (
            highs[-1] > highs[-2]
            or lows[-1] > lows[-2]
        )

    return False


# =========================================================
# MARKET BIAS
# =========================================================
def get_market_bias(df: pd.DataFrame) -> Dict:
    """Determine market bias using swing structure analysis."""
    
    swings = detect_swings(df, window=2)

    # Prevent empty dataframe errors
    if swings.empty:
        return {
            "bias": "neutral",
            "confidence": 0.0
        }

    # Make sure type column exists
    if "type" not in swings.columns:
        return {
            "bias": "neutral",
            "confidence": 0.0
        }

    # Remove non-swings
    swings = swings[swings["type"] != "none"]

    # Need enough swings
    if len(swings) < 4:
        return {
            "bias": "neutral",
            "confidence": 0.0
        }

    highs = swings[swings["type"] == "high"]
    lows = swings[swings["type"] == "low"]

    bullish_points = 0
    bearish_points = 0

    # Higher highs
    if len(highs) >= 2:
        if highs.iloc[-1]["price"] > highs.iloc[-2]["price"]:
            bullish_points += 1
        else:
            bearish_points += 1

    # Higher lows
    if len(lows) >= 2:
        if lows.iloc[-1]["price"] > lows.iloc[-2]["price"]:
            bullish_points += 1
        else:
            bearish_points += 1

    total = bullish_points + bearish_points

    if total == 0:
        return {
            "bias": "neutral",
            "confidence": 0.0
        }

    bullish_confidence = bullish_points / total
    bearish_confidence = bearish_points / total

    if bullish_confidence > bearish_confidence:
        return {
            "bias": "bullish",
            "confidence": round(bullish_confidence, 2)
        }

    elif bearish_confidence > bullish_confidence:
        return {
            "bias": "bearish",
            "confidence": round(bearish_confidence, 2)
        }

    return {
        "bias": "neutral",
        "confidence": 0.0
    }


# =========================================================
# SIGNAL ENGINE
# =========================================================
def generate_smc_signals(
    df: pd.DataFrame,
    structure_window: int = 5,
    liquidity_lookback: int = 10,
) -> List[Dict]:

    df = standardize_ohlc(df)

    swings = detect_swings(
        df,
        window=structure_window
    )

    signals = []

    for i in range(len(df)):

        current_swings = swings[
            swings["index"] <= i
        ]

        bias_info = get_market_bias(
            df.iloc[:i + 1]
        )

        bias = bias_info["bias"]

        bos = detect_bos_swing(
            df.iloc[:i + 1],
            current_swings
        )

        choch = detect_choch_swing(
            df.iloc[:i + 1],
            current_swings,
            bias
        )

        liquidity = detect_liquidity_zone(
            df,
            i,
            lookback=liquidity_lookback
        )

        order_block = None

        if bos and liquidity:
            order_block = bias

        signals.append({
            "trend": bias,
            "bos": bos,
            "choch": choch,
            "liquidity_zone": liquidity,
            "order_block": order_block,
        })

    return signals


# =========================================================
# TRADE SETUP
# =========================================================
def generate_trade_setup(df: pd.DataFrame) -> Dict:

    df = standardize_ohlc(df)

    signals = generate_smc_signals(df)

    recent = signals[-10:]

    trend_count = {}

    for s in recent:
        trend = s["trend"]
        trend_count[trend] = (
            trend_count.get(trend, 0) + 1
        )

    bias = (
        max(trend_count, key=trend_count.get)
        if trend_count
        else "neutral"
    )

    has_bos = any(s["bos"] for s in recent)
    has_choch = any(s["choch"] for s in recent)
    has_liquidity = any(
        s["liquidity_zone"]
        for s in recent
    )

    confidence = 0.0

    if bias in ["bullish", "bearish"]:
        confidence += 0.4

    if has_bos:
        confidence += 0.3

    if has_choch:
        confidence += 0.2

    if has_liquidity:
        confidence += 0.1

    confidence = min(confidence, 1.0)

    current_price = df.iloc[-1]["close"]

    reasoning = []

    reasoning.append(f"Market bias: {bias}")

    if has_bos:
        reasoning.append(
            "Break of Structure detected"
        )

    if has_choch:
        reasoning.append(
            "CHOCH confirmed"
        )

    if has_liquidity:
        reasoning.append(
            "Liquidity zone detected"
        )

    if bias == "bullish" and has_bos:

        entry = current_price + 0.0003
        sl = current_price - 0.0020
        tp = entry + ((entry - sl) * 2.5)

    elif bias == "bearish" and has_bos:

        entry = current_price - 0.0003
        sl = current_price + 0.0020
        tp = entry - ((sl - entry) * 2.5)

    else:
        return {
            "bias": "neutral",
            "entry": None,
            "stop_loss": None,
            "take_profit": None,
            "rr": None,
            "confidence": round(confidence, 2),
            "reasoning": reasoning + [
                "No valid setup found"
            ]
        }

    return {
        "bias": bias,
        "entry": round(entry, 5),
        "stop_loss": round(sl, 5),
        "take_profit": round(tp, 5),
        "rr": 2.5,
        "confidence": round(confidence, 2),
        "reasoning": reasoning
    }

# =========================================================
# HTF BIAS HELPER
# =========================================================
def get_bias(htf_df: pd.DataFrame) -> str:

    bias_info = get_market_bias(htf_df)

    return bias_info["bias"]


# =========================================================
# ENTRY SIGNAL
# =========================================================
def get_entry_signal(
    ltf_df: pd.DataFrame,
    bias: str
) -> Dict:

    if bias == "neutral":
        return {
            "entry": None,
            "sl": None,
            "tp": None,
            "bos": False,
            "liquidity": False
        }

    ltf_df = standardize_ohlc(ltf_df)

    swings = detect_swings(
        ltf_df,
        window=2
    )

    valid_swings = swings[
        swings["type"] != "none"
    ]

    if len(valid_swings) < 2:
        return {
            "entry": None,
            "sl": None,
            "tp": None,
            "bos": False,
            "liquidity": False
        }

    current_price = ltf_df.iloc[-1]["close"]

    last_swing = valid_swings.iloc[-1]

    bos_found = False

    if (
        bias == "bullish"
        and last_swing["type"] == "high"
        and current_price > last_swing["price"]
    ):
        bos_found = True

    elif (
        bias == "bearish"
        and last_swing["type"] == "low"
        and current_price < last_swing["price"]
    ):
        bos_found = True

    liquidity = detect_liquidity_zone(
        ltf_df,
        len(ltf_df) - 1,
        lookback=10
    )

    if not bos_found:
        return {
            "entry": None,
            "sl": None,
            "tp": None,
            "bos": False,
            "liquidity": liquidity is not None
        }

    if bias == "bullish":

        entry = current_price
        sl = current_price - 0.0020
        tp = current_price + 0.0040

    else:

        entry = current_price
        sl = current_price + 0.0020
        tp = current_price - 0.0040

    return {
        "entry": round(entry, 5),
        "sl": round(sl, 5),
        "tp": round(tp, 5),
        "bos": True,
        "liquidity": liquidity is not None
    }


# =========================================================
# SESSION FILTER
# =========================================================
def is_active_session() -> bool:

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    hour = now.hour

    london = 7 <= hour <= 16

    new_york = 12 <= hour <= 21

    return london or new_york


# =========================================================
# MULTI TF TRADE SETUP
# =========================================================
def generate_trade_setup_multi_tf(
    htf_df: pd.DataFrame,
    ltf_df: pd.DataFrame
) -> Dict:

    bias = get_bias(htf_df)

    entry_signal = get_entry_signal(
        ltf_df,
        bias
    )

    in_session = is_active_session()

    confidence = 0.0

    reasoning = []

    reasoning.append(
        f"Higher timeframe bias: {bias}"
    )

    if bias in ["bullish", "bearish"]:
        confidence += 0.4

    if entry_signal["bos"]:
        confidence += 0.3
        reasoning.append(
            "BOS confirmed on lower timeframe"
        )

    if entry_signal["liquidity"]:
        confidence += 0.1
        reasoning.append(
            "Liquidity sweep detected"
        )

    swings = detect_swings(
        ltf_df,
        window=2
    )

    choch = detect_choch_swing(
        ltf_df,
        swings,
        bias
    )

    if choch:
        confidence += 0.1
        reasoning.append(
            "CHOCH detected"
        )

    if in_session:
        confidence += 0.1
        reasoning.append(
            "Inside active session"
        )

    confidence = min(confidence, 1.0)

    if (
        bias == "neutral"
        or not entry_signal["bos"]
    ):

        return {
            "bias": bias,
            "entry": None,
            "stop_loss": None,
            "take_profit": None,
            "rr": None,
            "confidence": round(confidence, 2),
            "reasoning": reasoning + [
                "No valid setup"
            ]
        }

    return {
        "bias": bias,
        "entry": entry_signal["entry"],
        "stop_loss": entry_signal["sl"],
        "take_profit": entry_signal["tp"],
        "rr": 2.0,
        "confidence": round(confidence, 2),
        "reasoning": reasoning
    }


def prepare_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Attach the shared SMC signal columns to normalized OHLC data."""
    candles = standardize_ohlc(df)
    signals = generate_smc_signal_frame(candles)
    prepared = candles.copy()
    prepared["trend"] = signals["bias"].replace({"unknown": "neutral"})
    prepared["bos"] = signals["bos"]
    prepared["choch"] = signals["choch"]
    prepared["liquidity_zone"] = signals["liquidity_zone"]
    prepared["order_block"] = signals["order_block"]
    return prepared