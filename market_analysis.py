"""Multi-timeframe price-action and Smart Money Concepts analysis."""

from typing import Any, Dict, Mapping, Optional, Sequence

import pandas as pd

from smc.detection import standardize_ohlc


DEFAULT_TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1")


def _confirmed_swings(
    df: pd.DataFrame, window: int
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    highs: list[tuple[int, float]] = []
    lows: list[tuple[int, float]] = []

    for index in range(window, len(df) - window):
        high = float(df["high"].iloc[index])
        low = float(df["low"].iloc[index])
        previous_highs = df["high"].iloc[index - window:index]
        next_highs = df["high"].iloc[index + 1:index + window + 1]
        previous_lows = df["low"].iloc[index - window:index]
        next_lows = df["low"].iloc[index + 1:index + window + 1]

        if high > previous_highs.max() and high > next_highs.max():
            highs.append((index, high))
        if low < previous_lows.min() and low < next_lows.min():
            lows.append((index, low))

    return highs, lows


def analyze_timeframe(
    frame: pd.DataFrame,
    timeframe: str,
    swing_window: int = 2,
    liquidity_lookback: int = 10,
) -> Dict[str, Any]:
    """Summarize confirmed structure and the latest closed candle."""
    df = standardize_ohlc(frame)
    if len(df) < max(2 * swing_window + 1, liquidity_lookback + 2):
        return {
            "timeframe": timeframe,
            "bias": "neutral",
            "bos": None,
            "choch": False,
            "liquidity_sweep": None,
            "order_block": None,
            "close": float(df["close"].iloc[-1]) if not df.empty else None,
            "bar_time": df["time"].iloc[-1] if not df.empty else None,
            "reason": "Not enough closed candles for this analysis window.",
        }

    swing_highs, swing_lows = _confirmed_swings(df, swing_window)
    higher_highs = len(swing_highs) >= 2 and swing_highs[-1][1] > swing_highs[-2][1]
    higher_lows = len(swing_lows) >= 2 and swing_lows[-1][1] > swing_lows[-2][1]
    lower_highs = len(swing_highs) >= 2 and swing_highs[-1][1] < swing_highs[-2][1]
    lower_lows = len(swing_lows) >= 2 and swing_lows[-1][1] < swing_lows[-2][1]

    if higher_highs and higher_lows:
        bias = "bullish"
    elif lower_highs and lower_lows:
        bias = "bearish"
    else:
        bias = "neutral"

    previous_close = float(df["close"].iloc[-2])
    close = float(df["close"].iloc[-1])
    high_level = swing_highs[-1][1] if swing_highs else None
    low_level = swing_lows[-1][1] if swing_lows else None

    bos: Optional[str] = None
    if high_level is not None and previous_close <= high_level < close:
        bos = "bullish"
    elif low_level is not None and previous_close >= low_level > close:
        bos = "bearish"

    choch = (
        bias == "bullish" and low_level is not None
        and previous_close >= low_level > close
    ) or (
        bias == "bearish" and high_level is not None
        and previous_close <= high_level < close
    )

    prior = df.iloc[-liquidity_lookback - 1:-1]
    prior_high = float(prior["high"].max())
    prior_low = float(prior["low"].min())
    last = df.iloc[-1]
    if float(last["high"]) > prior_high and close < prior_high:
        liquidity_sweep: Optional[str] = "highs"
    elif float(last["low"]) < prior_low and close > prior_low:
        liquidity_sweep = "lows"
    else:
        liquidity_sweep = None

    order_block: Optional[Dict[str, Any]] = None
    if bos:
        for index in range(len(df) - 2, max(-1, len(df) - 7), -1):
            candle = df.iloc[index]
            is_bearish = float(candle["close"]) < float(candle["open"])
            is_bullish = float(candle["close"]) > float(candle["open"])
            if (bos == "bullish" and is_bearish) or (bos == "bearish" and is_bullish):
                order_block = {
                    "direction": bos,
                    "time": candle["time"],
                    "low": float(candle["low"]),
                    "high": float(candle["high"]),
                }
                break

    reasons = []
    if bias != "neutral":
        reasons.append(f"{bias.title()} swing structure")
    if bos:
        reasons.append(f"{bos.title()} break of structure")
    if choch:
        reasons.append("Change of character against the prior structure")
    if liquidity_sweep:
        reasons.append(f"Liquidity sweep of {liquidity_sweep}")
    if order_block:
        reasons.append(f"{bos.title()} order block confirmed by BOS")
    if not reasons:
        reasons.append("No confirmed directional structure or trigger")

    return {
        "timeframe": timeframe,
        "bias": bias,
        "bos": bos,
        "choch": bool(choch),
        "liquidity_sweep": liquidity_sweep,
        "order_block": order_block,
        "swing_high": high_level,
        "swing_low": low_level,
        "close": close,
        "bar_time": df["time"].iloc[-1],
        "reason": "; ".join(reasons),
    }


def _format_price(value: float) -> str:
    decimals = 3 if abs(value) >= 20 else 5
    return f"{value:.{decimals}f}"


def analyze_market(
    frames: Mapping[str, pd.DataFrame],
    entry_timeframe: str = "M15",
    timeframe_order: Sequence[str] = DEFAULT_TIMEFRAMES,
) -> Dict[str, Any]:
    """Analyze supplied timeframe frames and produce an explainable setup note."""
    normalized_entry = entry_timeframe.upper()
    if normalized_entry not in frames:
        raise ValueError(f"Entry timeframe {normalized_entry} is not available.")

    analyses = {
        timeframe: analyze_timeframe(frames[timeframe], timeframe)
        for timeframe in timeframe_order
        if timeframe in frames
    }
    if normalized_entry not in analyses:
        analyses[normalized_entry] = analyze_timeframe(
            frames[normalized_entry], normalized_entry
        )

    entry = analyses[normalized_entry]
    direction = entry["bos"]
    higher_timeframes = [
        result for timeframe, result in analyses.items()
        if timeframe != normalized_entry and result["bias"] != "neutral"
    ]
    aligned = sum(result["bias"] == direction for result in higher_timeframes)
    alignment_score = round(50 * aligned / len(higher_timeframes)) if higher_timeframes else 0

    confidence_score = min(
        100,
        alignment_score
        + (20 if direction else 0)
        + (15 if entry["order_block"] else 0)
        + (10 if entry["liquidity_sweep"] else 0)
        + (5 if entry["choch"] else 0),
    )

    recommendation: Dict[str, Any] = {
        "direction": None,
        "entry_zone": None,
        "stop_loss": None,
        "take_profit": None,
        "risk_reward": None,
        "confidence_score": confidence_score,
        "reasons": [],
    }

    zone = entry["order_block"]
    if direction and zone and aligned:
        entry_price = (zone["low"] + zone["high"]) / 2
        stop_loss = zone["low"] if direction == "bullish" else zone["high"]
        risk = abs(entry_price - stop_loss)
        if risk > 0:
            target = entry_price + 2 * risk if direction == "bullish" else entry_price - 2 * risk
            recommendation.update({
                "direction": direction,
                "entry_zone": [zone["low"], zone["high"]],
                "stop_loss": stop_loss,
                "take_profit": target,
                "risk_reward": 2.0,
                "reasons": [
                    f"{normalized_entry} {direction} BOS confirmed with an opposite-candle order block.",
                    f"{aligned} higher timeframe(s) align with the setup.",
                ],
            })

    if recommendation["direction"]:
        side = "BUY" if direction == "bullish" else "SELL"
        low, high = recommendation["entry_zone"]
        message = (
            f"Potential {side} setup on {normalized_entry} near "
            f"{_format_price(low)}–{_format_price(high)}; "
            f"SL {_format_price(recommendation['stop_loss'])}, "
            f"indicative 2R target {_format_price(recommendation['take_profit'])}. "
            f"Confidence score {confidence_score}/100 (heuristic, not a probability). "
            f"Why: {' '.join(recommendation['reasons'])}"
        )
    else:
        message = (
            f"No confirmed {normalized_entry} trade setup. "
            "Wait for a BOS, a confirmed order block, and higher-timeframe alignment. "
            f"Current heuristic score: {confidence_score}/100."
        )

    return {
        "entry_timeframe": normalized_entry,
        "timeframes": analyses,
        "recommendation": recommendation,
        "message": message,
        "disclaimer": (
            "Analysis only, not financial advice or an instruction to trade. "
            "No order has been or will be placed. Verify prices, spread, risk, "
            "and broker conditions independently."
        ),
    }
