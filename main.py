"""Interactive, analysis-only Forex assistant."""

from datetime import datetime, timezone
from typing import Any, Dict

from analyzer import analyze_market as analyze_text
from market_analysis import DEFAULT_TIMEFRAMES, analyze_market
from mt5_connect import connect, shutdown
from mt5_data import get_multi_tf_data
from retriever import query_knowledge
from storage.journal import TradeJournal
from visualization import plot_market_analysis


def _show_market_analysis(
    symbol: str,
    entry_timeframe: str,
    source: str,
    journal: TradeJournal,
) -> None:
    if entry_timeframe not in DEFAULT_TIMEFRAMES:
        print(
            f"Unsupported entry timeframe {entry_timeframe}. "
            f"Choose from: {', '.join(DEFAULT_TIMEFRAMES)}"
        )
        return

    print(f"\nConnecting to MT5 for {symbol.upper()}...")
    if not connect():
        print("MT5 connection failed. Check the terminal and account login.")
        return

    try:
        data = get_multi_tf_data(symbol)
        frames = data.get("frames")
        errors = data.get("errors", {})
        resolved_symbol = data.get("symbol", symbol.upper())
        if not isinstance(frames, dict) or not frames:
            raise RuntimeError("MT5 returned no usable timeframe data.")
        if entry_timeframe not in frames:
            detail = errors.get(entry_timeframe, "No bars returned.")
            raise RuntimeError(
                f"Entry timeframe {entry_timeframe} is unavailable: {detail}"
            )

        report = analyze_market(frames, entry_timeframe=entry_timeframe)
        print(f"\n{resolved_symbol} MULTI-TIMEFRAME SMC ANALYSIS")
        print("=" * 58)
        print(f"{'TF':<6}{'Bias':<12}{'BOS':<12}{'CHoCH':<9}Order block")
        for timeframe, result in report["timeframes"].items():
            order_block = result.get("order_block")
            zone_text = (
                f"{order_block['low']:.5f}–{order_block['high']:.5f}"
                if order_block else "—"
            )
            print(
                f"{timeframe:<6}{result['bias']:<12}"
                f"{(result['bos'] or '—'):<12}"
                f"{('yes' if result['choch'] else '—'):<9}{zone_text}"
            )

        print("\nTRADE IDEA (NOT AN ORDER)")
        print(report["message"])
        print(f"\nDisclaimer: {report['disclaimer']}")

        entry_result = report["recommendation"]
        zone = entry_result["entry_zone"]
        setup: Dict[str, Any] = {
            "bias": entry_result["direction"] or report["timeframes"][entry_timeframe]["bias"],
            "entry": sum(zone) / 2 if zone else None,
            "stop_loss": entry_result["stop_loss"],
            "take_profit": entry_result["take_profit"],
            "rr": entry_result["risk_reward"],
            "confidence": entry_result["confidence_score"] / 100,
            "reasoning": entry_result["reasons"],
        }
        entry_frame = frames[entry_timeframe]
        journal.log_setup(
            resolved_symbol,
            source=source,
            setup=setup,
            ltf_df=entry_frame,
            entry_index=len(entry_frame) - 1,
        )
        print("\nAnalysis saved to the local trade journal.")

        if input("\nPlot all available timeframes? (y/n): ").strip().lower() == "y":
            plot_market_analysis(frames, report, resolved_symbol).show()
    except Exception as exc:
        print(f"MT5 analysis failed ({type(exc).__name__}): {exc}")
    finally:
        shutdown()


def _show_help() -> None:
    print(
        "\nCOMMANDS\n"
        "  live <SYMBOL> [ENTRY_TF]     Fetch MT5 data and analyze all timeframes\n"
        "  analyze <SYMBOL> [ENTRY_TF]  Same analysis, saved as a pre-market review\n"
        "  <market text>                Rule-based SMC text analysis with local notes\n"
        "  help                         Show this help\n"
        "  exit                         Show this session's journal summary and quit\n"
        f"\nTIMEFRAMES: {', '.join(DEFAULT_TIMEFRAMES)}\n"
        "Default entry timeframe: M15. Specify another timeframe to change it.\n"
        "This version is analysis-only: it does not place or modify MT5 orders.\n"
        "Confidence is a heuristic score, not a probability or a guarantee."
    )


def main() -> None:
    print("=" * 58)
    print("FOREX SMC ANALYSIS ASSISTANT (ANALYSIS ONLY)")
    print("=" * 58)
    print("Commands: live EURUSD [M15] | analyze GBPUSD [H1] | help | exit")
    print("Text analysis is available without loading the knowledge base at startup.")

    session_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    journal = TradeJournal(session_id=session_id)

    while True:
        user_input = input("\nForex AI> ").strip()
        if not user_input:
            continue

        parts = user_input.split()
        command = parts[0].lower()

        if command == "help":
            _show_help()
            continue
        if command == "exit":
            print(journal.summary_text(session_id=session_id))
            return
        if command in {"live", "analyze"}:
            symbol = parts[1] if len(parts) > 1 else "EURUSD"
            entry_timeframe = parts[2].upper() if len(parts) > 2 else "M15"
            _show_market_analysis(
                symbol,
                entry_timeframe,
                source=command,
                journal=journal,
            )
            continue

        try:
            context = query_knowledge(user_input)
            print(analyze_text(user_input, context))
        except Exception as exc:
            print(f"Text analysis failed ({type(exc).__name__}): {exc}")


if __name__ == "__main__":
    main()
