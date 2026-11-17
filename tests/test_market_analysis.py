import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from market_analysis import DEFAULT_TIMEFRAMES, analyze_market, analyze_timeframe
import mt5_data
from visualization import plot_market_analysis


def _uptrend_frame(periods: int = 48) -> pd.DataFrame:
    index = np.arange(periods)
    close = 1.10 + index * 0.0001 + 0.0005 * np.sin(index * np.pi / 4)
    return pd.DataFrame({
        "time": pd.date_range("2025-01-01", periods=periods, freq="15min", tz="UTC"),
        "open": close - 0.00005,
        "high": close + 0.0001,
        "low": close - 0.0001,
        "close": close,
    })


class MarketAnalysisTests(unittest.TestCase):
    def test_mt5_loader_drops_the_current_candle(self) -> None:
        rates = [
            {
                "time": timestamp,
                "open": 1.1,
                "high": 1.101,
                "low": 1.099,
                "close": 1.1,
                "tick_volume": 10,
            }
            for timestamp in (1_700_000_000, 1_700_000_060, 1_700_000_120)
        ]
        with (
            patch.object(mt5_data.mt5, "symbol_select", return_value=True),
            patch.object(mt5_data.mt5, "copy_rates_from_pos", return_value=rates),
        ):
            result = mt5_data._get_closed_data(
                "EURUSD", 2, mt5_data.mt5.TIMEFRAME_M1
            )

        self.assertEqual(len(result), 2)
        self.assertEqual(result["time"].iloc[-1].timestamp(), 1_700_000_060)

    def test_short_history_returns_neutral_explanation(self) -> None:
        result = analyze_timeframe(_uptrend_frame(5), "M15")

        self.assertEqual(result["bias"], "neutral")
        self.assertIsNone(result["bos"])
        self.assertIn("Not enough", result["reason"])

    def test_confirmed_bos_and_order_block_produce_explainable_candidate(self) -> None:
        entry_frame = _uptrend_frame()
        initial = analyze_timeframe(entry_frame, "M15")
        swing_high = initial["swing_high"]
        self.assertIsNotNone(swing_high)

        previous_close = swing_high - 0.0002
        entry_frame.loc[entry_frame.index[-2], ["open", "high", "low", "close"]] = [
            swing_high - 0.0001,
            swing_high - 0.00005,
            swing_high - 0.0003,
            previous_close,
        ]
        entry_frame.loc[entry_frame.index[-1], ["open", "high", "low", "close"]] = [
            previous_close,
            swing_high + 0.0003,
            previous_close - 0.00005,
            swing_high + 0.0002,
        ]

        other_frames = _uptrend_frame()
        frames = {timeframe: other_frames.copy() for timeframe in DEFAULT_TIMEFRAMES}
        frames["M15"] = entry_frame

        report = analyze_market(frames, entry_timeframe="M15")
        recommendation = report["recommendation"]

        self.assertEqual(report["timeframes"]["M15"]["bos"], "bullish")
        self.assertIsNotNone(report["timeframes"]["M15"]["order_block"])
        self.assertEqual(recommendation["direction"], "bullish")
        self.assertEqual(recommendation["risk_reward"], 2.0)
        self.assertIn("not a probability", report["message"])
        self.assertIn("No order", report["disclaimer"])

        figure = plot_market_analysis(frames, report, "EURUSD")
        candle_traces = [
            trace for trace in figure.data
            if trace.type == "candlestick"
        ]
        self.assertEqual(len(candle_traces), len(DEFAULT_TIMEFRAMES))
        self.assertGreaterEqual(len(figure.layout.shapes), 1)

    def test_no_setup_is_proposed_without_entry_timeframe_trigger(self) -> None:
        frame = pd.DataFrame({
            "time": pd.date_range("2025-01-01", periods=40, freq="h", tz="UTC"),
            "open": [1.1] * 40,
            "high": [1.101] * 40,
            "low": [1.099] * 40,
            "close": [1.1] * 40,
        })

        report = analyze_market({"M15": frame, "H1": frame}, "M15")

        self.assertIsNone(report["recommendation"]["direction"])
        self.assertIn("No confirmed", report["message"])


if __name__ == "__main__":
    unittest.main()
