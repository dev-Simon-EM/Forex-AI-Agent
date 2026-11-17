"""SMC package for detecting Smart Money Concepts in OHLC price data."""

from .detection import (
    generate_smc_signal_frame,
    standardize_ohlc,
    is_swing_high,
    is_swing_low,
    detect_bos,
    detect_choch,
    detect_liquidity_zone,
    detect_order_block,
    detect_market_structure,
)

__all__ = [
    "generate_smc_signal_frame",
    "standardize_ohlc",
    "is_swing_high",
    "is_swing_low",
    "detect_bos",
    "detect_choch",
    "detect_liquidity_zone",
    "detect_order_block",
    "detect_market_structure",
]
