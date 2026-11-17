# Forex AI Agent

A Python-based, rule-driven Smart Money Concepts (SMC) assistant for manual
forex analysis. It reads market data from MetaTrader 5, compares multiple
timeframes, marks price-action structures and order blocks, and presents an
explainable trade idea. It does **not** place or modify orders.

## Current capabilities

- **Multi-timeframe MT5 analysis:** M1, M5, M15, M30, H1, H4, D1, and W1. The
  most recent forming MT5 candle is excluded from analysis.
- **Price action:** confirmed swing highs/lows, HH/HL and LH/LL structure,
  candle-close BOS, CHoCH, and simple liquidity sweeps.
- **Order blocks:** identifies the most recent opposing candle before a BOS.
- **Trade idea:** when the selected entry timeframe has a BOS and order block
  aligned with another analyzed timeframe, reports the zone, midpoint, a
  structural stop, and an indicative 2R target.
- **Heuristic confluence score:** a 0–100 score based on timeframe alignment,
  BOS, order block, liquidity sweep, and CHoCH. It is not a probability,
  forecast, or guarantee.
- **Interactive Plotly chart:** one panel per available timeframe, with candle
  data, BOS/CHoCH markers, order-block zones, and suggested levels.
- **Local journaling:** records analysis in SQLite and CSV. New live analyses
  remain pending until there are later candles to evaluate.
- **Text concept mode:** retrieves local SMC notes and applies simple
  keyword-based rules; this mode is not an LLM and does not analyze live prices.

## Run

Install the packages listed in `requirements.txt`, install and open the
MetaTrader 5 terminal, and sign in to the account whose market data you want to
inspect. From the project directory:

```powershell
python main.py
```

Commands:

```text
live EURUSD              # Analyze all available timeframes; use M15 as entry TF
live GBPUSD H1            # Analyze all timeframes; use H1 for the trade idea
analyze EURUSD H4          # Same analysis, tagged as a pre-market review
help
exit
```

Use a symbol available in the connected terminal. Broker suffixes are resolved
where possible. The CLI reports timeframes for which MT5 has no usable data.
Answer `y` to display the multi-timeframe chart.

## How a trade idea is formed

Swing points are confirmed only after the configured right-side candles have
closed. A BOS requires the latest close to cross the latest confirmed swing
level. An order block is the latest opposite-direction candle in the five
candles preceding that BOS. A candidate is shown only when the entry-timeframe
BOS and order block agree with at least one other timeframe's directional bias.
Otherwise the assistant says there is no confirmed setup.

The score is intentionally described as a **heuristic**. Its current
contributions are: up to 50 points for agreement among other directional
timeframes, 20 for BOS, 15 for an order block, 10 for a liquidity sweep, and 5
for CHoCH. Prices and the 2R target are analytical reference levels only;
spread, commissions, slippage, account currency, and broker constraints are not
modeled.

## Safety and execution status

This version is analysis-only. It does not submit, amend, or close MT5 orders,
and it does not calculate an executable volume. The existing MT5 order method
is a placeholder. Trade execution, user-granted permissions, account risk
limits, and order validation are **not implemented**. Any later execution
feature should be explicitly opt-in and enforce broker-side checks and
configured risk caps.

All trade ideas require independent review. This software is educational, not
financial advice. A score does not imply a chance of success; losses are
possible.

## Project layout

```text
main.py                 Interactive analysis-only CLI
market_analysis.py      Multi-timeframe SMC rules and trade idea
mt5_data.py             Closed-candle retrieval for standard MT5 timeframes
smc/detection.py        Shared SMC detection utilities
visualization/plotter.py Plotly price/action and multi-timeframe charts
storage/journal.py      SQLite/CSV analysis journal
analyzer.py             Rule-based text analysis
retriever.py            Local SMC-note retrieval
backtester.py           Experimental OHLC backtest engine
tests/                  Focused analysis regression tests
```

## Development checks

Run the focused market-analysis tests:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

The existing backtester is experimental; its results are not a substitute for
validated historical testing, realistic costs, or out-of-sample evaluation.
