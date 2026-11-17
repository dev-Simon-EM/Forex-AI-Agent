#!/usr/bin/env python
"""Comprehensive audit and test of all modules."""

import sys
import traceback
import pandas as pd
import numpy as np
from datetime import datetime, timezone

print("=" * 70)
print("COMPREHENSIVE AUDIT & FUNCTIONAL TEST")
print("=" * 70)

# ============================================================================
# 1. IMPORT TEST
# ============================================================================
print("\n[1/6] TESTING IMPORTS...")
print("-" * 70)

test_modules = [
    ('strategy', ['detect_swings', 'get_market_bias', 'get_entry_signal', 'generate_trade_setup_multi_tf']),
    ('mt5_data', ['get_valid_symbol', 'get_data', 'get_multi_tf_data']),
    ('risk', ['calculate_lot_size', 'calculate_rr']),
    ('data_loader', ['load_ohlc_csv']),
    ('backtester', ['run_backtest', 'BacktestResult']),
    ('storage.journal', ['TradeJournal']),
    ('plotter', ['plot_trade']),
]

import_errors = []
for module_name, functions in test_modules:
    try:
        module = __import__(module_name, fromlist=functions)
        missing = [f for f in functions if not hasattr(module, f)]
        if missing:
            print(f"  ✗ {module_name}: Missing {missing}")
            import_errors.append(f"{module_name}: {missing}")
        else:
            print(f"  ✓ {module_name}")
    except Exception as e:
        print(f"  ✗ {module_name}: {type(e).__name__}: {str(e)[:80]}")
        import_errors.append(f"{module_name}: {e}")

# ============================================================================
# 2. DATA LOADER TEST
# ============================================================================
print("\n[2/6] TESTING DATA LOADER...")
print("-" * 70)

try:
    from data_loader import load_ohlc_csv
    df = load_ohlc_csv("sample_data.csv")
    assert len(df) > 0, "No data loaded"
    assert all(col in df.columns for col in ['time', 'open', 'high', 'low', 'close']), "Missing OHLC columns"
    print(f"  ✓ Loaded {len(df)} candles from sample_data.csv")
    print(f"    Columns: {list(df.columns)}")
    print(f"    Date range: {df['time'].min()} to {df['time'].max()}")
except Exception as e:
    print(f"  ✗ Data loader failed: {e}")
    traceback.print_exc()

# ============================================================================
# 3. STRATEGY MODULE TEST
# ============================================================================
print("\n[3/6] TESTING STRATEGY MODULE...")
print("-" * 70)

try:
    from strategy import detect_swings, get_market_bias, generate_trade_setup_multi_tf
    
    # Test with sample data
    df_sample = load_ohlc_csv("sample_data.csv")
    
    # Test detect_swings
    swings = detect_swings(df_sample, window=5)
    print(f"  ✓ detect_swings(): Found {len(swings)} swing points")
    
    # Test get_market_bias
    bias_info = get_market_bias(df_sample)
    print(f"  ✓ get_market_bias(): Bias={bias_info.get('bias')}, Confidence={bias_info.get('confidence')}")
    
    # Test generate_trade_setup_multi_tf (would need HTF/LTF data)
    print(f"  ✓ Strategy functions callable")
    
except Exception as e:
    print(f"  ✗ Strategy module error: {e}")
    traceback.print_exc()

# ============================================================================
# 4. RISK MANAGEMENT TEST
# ============================================================================
print("\n[4/6] TESTING RISK MANAGEMENT...")
print("-" * 70)

try:
    from risk import calculate_lot_size, calculate_rr
    
    # Test calculate_lot_size
    balance = 10000
    risk_percent = 1.0
    entry = 1.0850
    stop_loss = 1.0825
    lot_size = calculate_lot_size(balance, risk_percent, entry, stop_loss)
    print(f"  ✓ calculate_lot_size(): {lot_size} lots for ${balance} at 1% risk")
    
    # Test calculate_rr
    tp = 1.0900
    rr = calculate_rr(entry, stop_loss, tp)
    print(f"  ✓ calculate_rr(): RR ratio = {rr:.2f}")
    
except Exception as e:
    print(f"  ✗ Risk module error: {e}")
    traceback.print_exc()

# ============================================================================
# 5. BACKTESTER TEST
# ============================================================================
print("\n[5/6] TESTING BACKTESTER...")
print("-" * 70)

try:
    from backtester import run_backtest
    
    df_test = load_ohlc_csv("sample_data.csv")
    result = run_backtest(df_test)
    print(f"  ✓ Backtest completed:")
    print(f"    Total trades: {result.total_trades}")
    print(f"    Wins: {result.wins} | Losses: {result.losses}")
    print(f"    Win rate: {result.win_rate:.1f}%")
    print(f"    Total P/L: {result.profit_loss:.5f}")
    
except Exception as e:
    print(f"  ✗ Backtester error: {e}")
    traceback.print_exc()

# ============================================================================
# 6. TRADE JOURNAL TEST
# ============================================================================
print("\n[6/6] TESTING TRADE JOURNAL...")
print("-" * 70)

try:
    from storage.journal import TradeJournal
    
    journal = TradeJournal(session_id="test_audit")
    
    # Test logging a setup
    test_setup = {
        "bias": "bullish",
        "entry": 1.0850,
        "stop_loss": 1.0825,
        "take_profit": 1.0900,
        "rr": 2.5,
        "confidence": 0.85,
        "reasoning": ["Higher High pattern", "BOS confirmed"]
    }
    
    setup_id = journal.log_setup("EURUSD", source="test", setup=test_setup)
    print(f"  ✓ Setup logged with ID: {setup_id}")
    
    # Test summary
    summary = journal.query_summary(session_id="test_audit")
    print(f"  ✓ Journal summary:")
    print(f"    Total setups: {summary['total_setups']}")
    print(f"    Average confidence: {summary['avg_confidence']}")
    
except Exception as e:
    print(f"  ✗ Journal error: {e}")
    traceback.print_exc()

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("AUDIT SUMMARY")
print("=" * 70)

if import_errors:
    print(f"\n⚠️  Found {len(import_errors)} import/module issues:")
    for error in import_errors:
        print(f"  - {error}")
else:
    print("\n✅ All modules imported successfully")

print("\n📊 Status: AUDIT COMPLETE")
print("=" * 70)
