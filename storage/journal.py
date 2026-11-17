import csv
import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional


class TradeJournal:
    """Journal and performance analytics for generated SMC setups."""

    def __init__(
        self,
        db_path: str = "data/trade_journal.db",
        csv_path: str = "data/trade_journal.csv",
        session_id: Optional[str] = None,
        write_csv: bool = True,
    ):
        self.db_path = Path(db_path)
        self.csv_path = Path(csv_path)
        self.session_id = session_id or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        self.write_csv = write_csv

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        if self.write_csv:
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.csv_path.exists():
                self._write_csv_header()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        with closing(sqlite3.connect(self.db_path)) as conn:
            with conn:
                yield conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS setups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    created_at TEXT,
                    symbol TEXT,
                    source TEXT,
                    bias TEXT,
                    entry REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    rr REAL,
                    confidence REAL,
                    bos INTEGER,
                    choch INTEGER,
                    liquidity INTEGER,
                    in_session INTEGER,
                    reasoning TEXT,
                    outcome TEXT,
                    outcome_simulated INTEGER
                )
                """
            )
            conn.commit()

    def _write_csv_header(self) -> None:
        with self.csv_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "session_id",
                    "created_at",
                    "symbol",
                    "source",
                    "bias",
                    "entry",
                    "stop_loss",
                    "take_profit",
                    "rr",
                    "confidence",
                    "bos",
                    "choch",
                    "liquidity",
                    "in_session",
                    "reasoning",
                    "outcome",
                    "outcome_simulated",
                ]
            )

    def log_setup(
        self,
        symbol: str,
        source: str,
        setup: Dict[str, Any],
        ltf_df: Optional[Any] = None,
        entry_index: Optional[int] = None,
    ) -> int:
        """Store a generated setup and attempt to simulate its outcome."""
        created_at = datetime.now(timezone.utc).isoformat()
        reasoning = setup.get("reasoning", [])
        reasoning_text = json.dumps(reasoning, ensure_ascii=False)
        bos_flag = any("Break of structure" in str(r) for r in reasoning)
        choch_flag = any("Change of character" in str(r) for r in reasoning)
        liquidity_flag = any("Liquidity" in str(r) for r in reasoning)
        in_session_flag = any("Within active trading session" in str(r) for r in reasoning)
        outcome = "pending"
        outcome_simulated = 0

        if ltf_df is not None and setup.get("entry") is not None:
            current_index = entry_index if entry_index is not None else len(ltf_df) - 1
            simulated = self.simulate_outcome(
                ltf_df,
                current_index=current_index,
                bias=setup.get("bias", "neutral"),
                entry=setup["entry"],
                stop_loss=setup.get("stop_loss"),
                take_profit=setup.get("take_profit"),
            )
            if simulated is not None:
                outcome = simulated
                outcome_simulated = 1

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO setups (
                    session_id,
                    created_at,
                    symbol,
                    source,
                    bias,
                    entry,
                    stop_loss,
                    take_profit,
                    rr,
                    confidence,
                    bos,
                    choch,
                    liquidity,
                    in_session,
                    reasoning,
                    outcome,
                    outcome_simulated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.session_id,
                    created_at,
                    symbol,
                    source,
                    setup.get("bias"),
                    setup.get("entry"),
                    setup.get("stop_loss"),
                    setup.get("take_profit"),
                    setup.get("rr"),
                    setup.get("confidence"),
                    int(bos_flag),
                    int(choch_flag),
                    int(liquidity_flag),
                    int(in_session_flag),
                    reasoning_text,
                    outcome,
                    outcome_simulated,
                ),
            )
            row_id = cursor.lastrowid
            conn.commit()

        if self.write_csv:
            self._append_csv_row(
                {
                    "session_id": self.session_id,
                    "created_at": created_at,
                    "symbol": symbol,
                    "source": source,
                    "bias": setup.get("bias"),
                    "entry": setup.get("entry"),
                    "stop_loss": setup.get("stop_loss"),
                    "take_profit": setup.get("take_profit"),
                    "rr": setup.get("rr"),
                    "confidence": setup.get("confidence"),
                    "bos": int(bos_flag),
                    "choch": int(choch_flag),
                    "liquidity": int(liquidity_flag),
                    "in_session": int(in_session_flag),
                    "reasoning": reasoning_text,
                    "outcome": outcome,
                    "outcome_simulated": outcome_simulated,
                }
            )

        return row_id

    def _append_csv_row(self, row: Dict[str, Any]) -> None:
        with self.csv_path.open("a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=row.keys())
            writer.writerow(row)

    def simulate_outcome(
        self,
        ltf_df: Any,
        current_index: int,
        bias: str,
        entry: float,
        stop_loss: float,
        take_profit: float,
    ) -> Optional[str]:
        """Simulate whether TP or SL is hit first from the next candle onward."""
        if current_index >= len(ltf_df) - 1:
            return None

        direction = "long" if bias == "bullish" else "short"
        for idx in range(current_index + 1, len(ltf_df)):
            row = ltf_df.iloc[idx]
            low = float(row["low"])
            high = float(row["high"])

            hit_sl = low <= stop_loss if direction == "long" else high >= stop_loss
            hit_tp = high >= take_profit if direction == "long" else low <= take_profit

            if hit_sl and hit_tp:
                distance_sl = abs(entry - stop_loss)
                distance_tp = abs(take_profit - entry)
                return "win" if distance_tp <= distance_sl else "loss"
            if hit_tp:
                return "win"
            if hit_sl:
                return "loss"

        return None

    def query_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Return aggregate performance metrics for a session or all data."""
        where_clause = ""
        params: List[Any] = []
        if session_id:
            where_clause = "WHERE session_id = ?"
            params.append(session_id)

        with self._connect() as conn:
            cursor = conn.cursor()

            def count(condition: str = "") -> int:
                where = where_clause
                if condition:
                    where += (" AND " if where else "WHERE ") + condition
                cursor.execute(f"SELECT COUNT(*) FROM setups {where}", params)
                return cursor.fetchone()[0]

            total = count()
            wins = count("outcome = 'win'")
            losses = count("outcome = 'loss'")
            bos_total = count("bos = 1")
            bos_wins = count("bos = 1 AND outcome = 'win'")
            choch_total = count("choch = 1")
            choch_wins = count("choch = 1 AND outcome = 'win'")
            liquidity_total = count("liquidity = 1")
            liquidity_wins = count("liquidity = 1 AND outcome = 'win'")
            cursor.execute(f"SELECT AVG(confidence) FROM setups {where_clause}", params)
            avg_confidence = cursor.fetchone()[0] or 0.0

        return {
            "total_setups": total,
            "wins": wins,
            "losses": losses,
            "pending": total - wins - losses,
            "win_rate": (wins / total * 100.0) if total else 0.0,
            "bos_total": bos_total,
            "bos_wins": bos_wins,
            "bos_win_rate": (bos_wins / bos_total * 100.0) if bos_total else 0.0,
            "choch_total": choch_total,
            "choch_wins": choch_wins,
            "choch_win_rate": (choch_wins / choch_total * 100.0) if choch_total else 0.0,
            "liquidity_total": liquidity_total,
            "liquidity_wins": liquidity_wins,
            "liquidity_win_rate": (liquidity_wins / liquidity_total * 100.0) if liquidity_total else 0.0,
            "avg_confidence": round(avg_confidence, 2),
        }

    def summary_text(self, session_id: Optional[str] = None) -> str:
        """Format a session summary report."""
        summary = self.query_summary(session_id=session_id)
        return (
            "Session Journal Summary\n"
            "=======================\n"
            f"Total setups: {summary['total_setups']}\n"
            f"Wins: {summary['wins']}\n"
            f"Losses: {summary['losses']}\n"
            f"Pending outcomes: {summary['pending']}\n"
            f"Overall win rate: {summary['win_rate']:.1f}%\n"
            f"Average confidence: {summary['avg_confidence']:.2f}\n"
            "\n"
            "Win rate by setup type:\n"
            f"  BOS setups: {summary['bos_wins']}/{summary['bos_total']} ({summary['bos_win_rate']:.1f}%)\n"
            f"  CHOCH setups: {summary['choch_wins']}/{summary['choch_total']} ({summary['choch_win_rate']:.1f}%)\n"
            f"  Liquidity sweeps: {summary['liquidity_wins']}/{summary['liquidity_total']} ({summary['liquidity_win_rate']:.1f}%)\n"
        )

    def export_csv(self, csv_path: Optional[str] = None) -> None:
        """Export all stored setups to CSV."""
        path = Path(csv_path or self.csv_path)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id, created_at, symbol, source, bias, entry, stop_loss, take_profit, rr, confidence, bos, choch, liquidity, in_session, reasoning, outcome, outcome_simulated FROM setups")
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]

        with path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(columns)
            writer.writerows(rows)
