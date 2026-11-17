"""Build reusable trade signal structures from SMC signal data."""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _build_confidence(signal: pd.Series) -> float:
    score = 0.0
    if signal.get("bos"):
        score += 35.0
    if signal.get("choch"):
        score += 25.0
    if signal.get("order_block") is not None:
        score += 20.0
    if signal.get("liquidity_zone") is not None:
        score += 15.0

    if signal.get("bias") == "unknown":
        score *= 0.4

    confidence = min(100.0, max(0.0, score))
    logger.debug("Signal confidence = %s for row %s", confidence, signal.get("time"))
    return confidence


def _build_order_block_list(signal: pd.Series) -> List[Dict[str, Any]]:
    order_block = signal.get("order_block")
    if order_block is None:
        return []
    return [order_block]


def _build_bos_list(signal: pd.Series) -> List[Dict[str, Any]]:
    if not signal.get("bos"):
        return []
    return [{
        "time": signal.get("time"),
        "bias": signal.get("bias"),
        "description": "Break of Structure detected",
    }]


def build_trade_signal(
    signal: pd.Series,
    entry_buffer: float = 0.0003,
    reward_ratio: float = 2.0,
) -> Dict[str, Any]:
    """Compose a structured trade signal from a row of SMC signal data."""
    bias = signal.get("bias", "unknown")
    current_price = float(signal.get("close", 0.0)) if "close" in signal.index else None
    direction = "long" if bias == "bullish" else "short" if bias == "bearish" else None

    entry = None
    sl = None
    tp = None

    if direction and signal.get("bos"):
        entry = float(signal.get("close", current_price))
        if entry is not None:
            if direction == "long":
                sl = float(signal.get("low", entry)) - entry_buffer
                tp = entry + (entry - sl) * reward_ratio
            else:
                sl = float(signal.get("high", entry)) + entry_buffer
                tp = entry - (sl - entry) * reward_ratio

    confidence = _build_confidence(signal)

    trade_signal = {
        "bias": bias,
        "bos": _build_bos_list(signal),
        "order_blocks": _build_order_block_list(signal),
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "confidence": confidence,
    }

    logger.debug("Built trade signal: %s", trade_signal)
    return trade_signal


def summarize_signal(signal: Dict[str, Any]) -> str:
    """Return a human-readable summary of the structured trade signal."""
    return (
        f"bias={signal['bias']}, bos={len(signal['bos'])}, "
        f"order_blocks={len(signal['order_blocks'])}, entry={signal['entry']}, "
        f"sl={signal['sl']}, tp={signal['tp']}, confidence={signal['confidence']:.1f}"
    )
