from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from strategy import prepare_signals


@dataclass
class Trade:
    entry_index: int
    exit_index: int
    direction: str
    entry: float
    sl: float
    tp: float
    outcome: str
    profit: float
    duration: int


@dataclass
class BacktestResult:
    trades: List[Trade]

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> int:
        return sum(1 for trade in self.trades if trade.outcome == "win")

    @property
    def losses(self) -> int:
        return sum(1 for trade in self.trades if trade.outcome == "loss")

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.wins / self.total_trades * 100

    @property
    def profit_loss(self) -> float:
        return sum(trade.profit for trade in self.trades)

    @property
    def avg_profit(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.profit_loss / self.total_trades

    def summary(self) -> str:
        return (
            f"Total trades: {self.total_trades}\n"
            f"Wins: {self.wins}\n"
            f"Losses: {self.losses}\n"
            f"Win rate: {self.win_rate:.1f}%\n"
            f"Profit/Loss: {self.profit_loss:.5f}\n"
            f"Avg profit per trade: {self.avg_profit:.5f}\n"
        )


def _simulate_trade(
    df: pd.DataFrame,
    start_index: int,
    direction: str,
    entry: float,
    sl: float,
    tp: float,
) -> Optional[Trade]:
    """Simulate a trade from entry until SL or TP is hit."""
    for j in range(start_index, len(df)):
        candle = df.iloc[j]
        low = candle["low"]
        high = candle["high"]

        if direction == "long":
            hit_sl = low <= sl
            hit_tp = high >= tp
        else:
            hit_sl = high >= sl
            hit_tp = low <= tp

        if hit_sl and hit_tp:
            distance_sl = abs(entry - sl)
            distance_tp = abs(tp - entry)
            outcome = "win" if distance_tp <= distance_sl else "loss"
        elif hit_tp:
            outcome = "win"
        elif hit_sl:
            outcome = "loss"
        else:
            continue

        profit = (
            tp - entry if direction == "long" and outcome == "win"
            else sl - entry if direction == "long" and outcome == "loss"
            else entry - tp if direction == "short" and outcome == "win"
            else entry - sl
        )

        return Trade(
            entry_index=start_index,
            exit_index=j,
            direction=direction,
            entry=entry,
            sl=sl,
            tp=tp,
            outcome=outcome,
            profit=profit,
            duration=j - start_index + 1,
        )

    return None


def _generate_entry_signals(df: pd.DataFrame) -> List[bool]:
    """Generate entry signals based on SMC BOS + trend confluence."""
    signals = []
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        bos = row.get("bos", False)
        trend = row.get("trend", "unknown")
        
        signal = (
            bos 
            and trend != "unknown" 
            and (trend == "bullish" or trend == "bearish")
        )
        
        signals.append(signal)
    
    return signals


def run_backtest(
    df: pd.DataFrame,
    reward_ratio: float = 1.5,
    stop_buffer: float = 0.0002,
) -> BacktestResult:
    """
    Run SMC-based backtest on OHLC data.
    
    Args:
        df: DataFrame with time, open, high, low, close
        reward_ratio: risk/reward ratio (default 1.5)
        stop_buffer: buffer distance for stop loss (default 0.0002)
    
    Returns:
        BacktestResult with all trades and performance metrics
    """
    df = prepare_signals(df)
    entry_signals = _generate_entry_signals(df)
    trades: List[Trade] = []
    index = 0

    while index < len(df) - 1:
        if not entry_signals[index]:
            index += 1
            continue

        row = df.iloc[index]
        trend = row["trend"]
        
        entry_bar = index + 1
        if entry_bar >= len(df):
            break
            
        entry_price = df.iloc[entry_bar]["open"]

        if trend == "bullish":
            swing_low = df.iloc[index]["low"]
            sl = swing_low - stop_buffer
            tp = entry_price + (entry_price - sl) * reward_ratio
            direction = "long"
        elif trend == "bearish":
            swing_high = df.iloc[index]["high"]
            sl = swing_high + stop_buffer
            tp = entry_price - (sl - entry_price) * reward_ratio
            direction = "short"
        else:
            index += 1
            continue

        trade = _simulate_trade(df, entry_bar, direction, entry_price, sl, tp)
        if trade is not None:
            trades.append(trade)
            index = trade.exit_index + 1
        else:
            index = entry_bar + 1

    return BacktestResult(trades=trades)
