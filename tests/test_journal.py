import tempfile
import unittest
from pathlib import Path

from storage.journal import TradeJournal


class TradeJournalTests(unittest.TestCase):
    def test_summary_can_query_all_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            journal = TradeJournal(
                db_path=str(Path(directory) / "journal.db"),
                csv_path=str(Path(directory) / "journal.csv"),
                write_csv=False,
            )

            summary = journal.query_summary()

        self.assertEqual(summary["total_setups"], 0)
        self.assertEqual(summary["wins"], 0)
        self.assertEqual(summary["pending"], 0)


if __name__ == "__main__":
    unittest.main()
