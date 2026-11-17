"""Persistent storage for trade signals and analysis results."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SignalStore:
    """Store and retrieve trade signals with persistence."""

    def __init__(self, storage_path: str = "data/signals.jsonl"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.touch()

    def save_signal(self, signal: Dict[str, Any]) -> None:
        """Append a trade signal to the persistent store."""
        with self.storage_path.open("a", encoding="utf-8") as f:
            json.dump(signal, f, default=str, ensure_ascii=False)
            f.write("\n")
        logger.info("Saved signal: %s", signal.get("bias", "unknown"))

    def load_signals(self) -> List[Dict[str, Any]]:
        """Load all stored signals from disk."""
        signals = []
        if not self.storage_path.exists():
            return signals

        with self.storage_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        signals.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning("Skipping malformed signal line: %s", e)
        return signals

    def get_success_rate(self, bias_filter: Optional[str] = None) -> float:
        """Calculate success rate for stored signals, optionally filtered by bias."""
        signals = self.load_signals()
        if not signals:
            return 0.0

        filtered = signals
        if bias_filter:
            filtered = [s for s in signals if s.get("bias") == bias_filter]

        if not filtered:
            return 0.0

        successful = sum(1 for s in filtered if s.get("outcome") == "win")
        rate = (successful / len(filtered)) * 100.0
        logger.info("Success rate for %s: %.1f%% (%d/%d)", bias_filter or "all", rate, successful, len(filtered))
        return rate

    def update_signal_outcome(self, signal_index: int, outcome: str) -> bool:
        """Update the outcome of a stored signal (win/loss)."""
        signals = self.load_signals()
        if signal_index >= len(signals):
            logger.error("Signal index %d out of range", signal_index)
            return False

        signals[signal_index]["outcome"] = outcome
        self._rewrite_signals(signals)
        logger.info("Updated signal %d outcome to %s", signal_index, outcome)
        return True

    def _rewrite_signals(self, signals: List[Dict[str, Any]]) -> None:
        """Rewrite the entire signal file with updated data."""
        with self.storage_path.open("w", encoding="utf-8") as f:
            for signal in signals:
                json.dump(signal, f, default=str, ensure_ascii=False)
                f.write("\n")
