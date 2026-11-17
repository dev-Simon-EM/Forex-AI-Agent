"""Visualization helpers for SMC signals and trade setups."""

import logging
from typing import Any, Dict, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from smc.detection import generate_smc_signal_frame

logger = logging.getLogger(__name__)


def _normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "time" not in df.columns:
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index().rename(columns={"index": "time"})
        else:
            raise ValueError("DataFrame must contain a 'time' column or a DatetimeIndex.")
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    if df["time"].isnull().any():
        raise ValueError("Invalid time values found in OHLC data.")
    required = {"open", "high", "low", "close"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {sorted(missing)}")
    return df.loc[:, ["time", "open", "high", "low", "close"]].sort_values("time").reset_index(drop=True)


def _get_age_text(signal: Dict[str, Any]) -> str:
    if signal.get("bias"):
        return f"Bias: {signal['bias'].title()} | Confidence: {signal.get('confidence', 0):.0f}%"
    return "SMC Trade Signal"


def _style_layout(fig: go.Figure, title: str, height: int = 800) -> go.Figure:
    fig.update_layout(
        title=title,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        height=height,
        plot_bgcolor="#0f0f15",
        paper_bgcolor="#0f0f15",
        legend=dict(bgcolor="rgba(0,0,0,0.35)", orientation="h", y=1.02, x=0),
        margin=dict(l=50, r=30, t=80, b=50),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#222", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#222", zeroline=False)
    return fig


def _add_signal_overlays(fig: go.Figure, df: pd.DataFrame, signal_df: pd.DataFrame) -> None:
    bos_signals = signal_df[signal_df["bos"] == True]
    choch_signals = signal_df[signal_df["choch"] == True]
    liquidity_signals = signal_df[signal_df["liquidity_zone"].notna()]

    if not bos_signals.empty:
        fig.add_trace(
            go.Scatter(
                x=bos_signals["time"],
                y=df.loc[bos_signals.index, "close"],
                mode="markers",
                marker=dict(symbol="diamond", size=12, color="#FF4D4D"),
                name="BOS",
            )
        )

    if not choch_signals.empty:
        fig.add_trace(
            go.Scatter(
                x=choch_signals["time"],
                y=df.loc[choch_signals.index, "high"] * 1.002,
                mode="text",
                text=["CHOCH"] * len(choch_signals),
                textposition="top center",
                textfont=dict(color="#F5DEB3", size=11),
                name="CHOCH",
            )
        )

    for _, row in liquidity_signals.iterrows():
        index = int(row.name)
        label = "Liquidity Highs" if row["liquidity_zone"] == "equal_highs" else "Liquidity Lows"
        top = df.at[index, "high"] * 1.0006 if row["liquidity_zone"] == "equal_highs" else df.at[index, "low"] * 1.0010
        bottom = df.at[index, "high"] * 0.9990 if row["liquidity_zone"] == "equal_highs" else df.at[index, "low"] * 0.9992
        fig.add_shape(
            type="rect",
            xref="x",
            yref="y",
            x0=row["time"],
            x1=row["time"],
            y0=bottom,
            y1=top,
            fillcolor="rgba(255,165,0,0.15)" if row["liquidity_zone"] == "equal_highs" else "rgba(135,206,235,0.15)",
            line=dict(width=0),
            layer="below",
        )
        fig.add_annotation(
            x=row["time"],
            y=top,
            text=label,
            showarrow=False,
            yshift=8,
            font=dict(color="#FFFFFF", size=10),
            bgcolor="rgba(0, 0, 0, 0.4)",
        )


def plot_smc_signals(
    df: pd.DataFrame,
    signals: Optional[pd.DataFrame] = None,
    title: str = "SMC Signal Analysis",
    height: int = 900,
) -> go.Figure:
    df = _normalize_ohlc(df)
    signals = signals if signals is not None else generate_smc_signal_frame(df)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=("Price Chart", "Signal Strength"),
        row_heights=[0.75, 0.25],
    )

    fig.add_trace(
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="OHLC",
        ),
        row=1,
        col=1,
    )

    _add_signal_overlays(fig, df, signals)

    trend_column = "bias" if "bias" in signals.columns else "trend"
    bias_values = signals[trend_column].map({"bullish": 1, "bearish": -1, "neutral": 0, "unknown": 0})
    fig.add_trace(
        go.Scatter(
            x=signals["time"],
            y=bias_values,
            mode="lines+markers",
            line=dict(color="#7289DA", width=2),
            marker=dict(size=6),
            name="Structure Bias",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(title=title, xaxis_rangeslider_visible=False, height=height, showlegend=True)
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Bias", row=2, col=1, tickvals=[-1, 0, 1], ticktext=["Bearish", "Neutral", "Bullish"])

    return _style_layout(fig, title, height)


def plot_trade_signal(signal: Dict[str, Any], df: pd.DataFrame) -> go.Figure:
    df = _normalize_ohlc(df)
    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="OHLC",
        )
    )

    if signal.get("entry") is not None:
        fig.add_hline(
            y=signal["entry"],
            line_dash="dash",
            line_color="#00FF9D",
            annotation_text=f"Entry: {signal['entry']:.5f}",
        )
    if signal.get("sl") is not None:
        fig.add_hline(
            y=signal["sl"],
            line_dash="dot",
            line_color="#FF4D4D",
            annotation_text=f"SL: {signal['sl']:.5f}",
        )
    if signal.get("tp") is not None:
        fig.add_hline(
            y=signal["tp"],
            line_dash="dot",
            line_color="#4ACBFF",
            annotation_text=f"TP: {signal['tp']:.5f}",
        )

    title = _get_age_text(signal)
    return _style_layout(fig, title, height=650)


def plot_multi_tf_smc(
    htf_df: pd.DataFrame,
    ltf_df: pd.DataFrame,
    htf_signals: Optional[pd.DataFrame] = None,
    ltf_signals: Optional[pd.DataFrame] = None,
    title: str = "Multi-Timeframe SMC Structure",
    height: int = 1000,
) -> go.Figure:
    htf_df = _normalize_ohlc(htf_df)
    ltf_df = _normalize_ohlc(ltf_df)
    htf_signals = htf_signals if htf_signals is not None else generate_smc_signal_frame(htf_df)
    ltf_signals = ltf_signals if ltf_signals is not None else generate_smc_signal_frame(ltf_df)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.08,
        subplot_titles=("Higher Timeframe", "Lower Timeframe"),
        row_heights=[0.5, 0.5],
    )

    fig.add_trace(
        go.Candlestick(
            x=htf_df["time"],
            open=htf_df["open"],
            high=htf_df["high"],
            low=htf_df["low"],
            close=htf_df["close"],
            name="HTF Price",
        ),
        row=1,
        col=1,
    )
    _add_signal_overlays(fig, htf_df, htf_signals)

    fig.add_trace(
        go.Candlestick(
            x=ltf_df["time"],
            open=ltf_df["open"],
            high=ltf_df["high"],
            low=ltf_df["low"],
            close=ltf_df["close"],
            name="LTF Price",
        ),
        row=2,
        col=1,
    )
    _add_signal_overlays(fig, ltf_df, ltf_signals)

    fig.update_layout(title=title, xaxis_rangeslider_visible=False, height=height, showlegend=True)
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Price", row=2, col=1)

    return _style_layout(fig, title, height)


def plot_market_analysis(
    frames: Dict[str, pd.DataFrame],
    analysis: Dict[str, Any],
    symbol: str,
) -> go.Figure:
    """Plot all available timeframe candles with confirmed SMC levels and zones."""
    timeframes = [
        timeframe for timeframe in analysis["timeframes"]
        if timeframe in frames and not frames[timeframe].empty
    ]
    if not timeframes:
        raise ValueError("No non-empty timeframe data is available to plot.")

    fig = make_subplots(
        rows=len(timeframes),
        cols=1,
        shared_xaxes=False,
        vertical_spacing=min(0.06, 0.3 / len(timeframes)),
        subplot_titles=[f"{symbol} · {timeframe}" for timeframe in timeframes],
    )
    entry_timeframe = analysis["entry_timeframe"]
    recommendation = analysis["recommendation"]

    for row_index, timeframe in enumerate(timeframes, start=1):
        df = _normalize_ohlc(frames[timeframe])
        result = analysis["timeframes"][timeframe]
        fig.add_trace(
            go.Candlestick(
                x=df["time"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name=f"{timeframe} candles",
                showlegend=(row_index == 1),
            ),
            row=row_index,
            col=1,
        )

        zone = result.get("order_block")
        if zone:
            color = (
                "rgba(0, 200, 120, 0.18)"
                if zone["direction"] == "bullish"
                else "rgba(240, 70, 70, 0.18)"
            )
            fig.add_shape(
                type="rect",
                x0=zone["time"],
                x1=df["time"].iloc[-1],
                y0=zone["low"],
                y1=zone["high"],
                fillcolor=color,
                line=dict(width=1, color=color.replace("0.18", "0.8")),
                layer="below",
                row=row_index,
                col=1,
            )

        if result.get("bos"):
            direction = result["bos"]
            fig.add_trace(
                go.Scatter(
                    x=[df["time"].iloc[-1]],
                    y=[df["close"].iloc[-1]],
                    mode="markers+text",
                    text=[f"{direction.upper()} BOS"],
                    textposition="top center",
                    marker=dict(
                        symbol="diamond",
                        size=11,
                        color="#00C878" if direction == "bullish" else "#F04646",
                    ),
                    name=f"{timeframe} BOS",
                    showlegend=(row_index == 1),
                ),
                row=row_index,
                col=1,
            )

        if result.get("choch"):
            fig.add_annotation(
                x=df["time"].iloc[-1],
                y=df["close"].iloc[-1],
                text="CHoCH",
                showarrow=True,
                arrowhead=2,
                ax=0,
                ay=-28,
                row=row_index,
                col=1,
            )

        if timeframe == entry_timeframe and recommendation.get("direction"):
            entry_low, entry_high = recommendation["entry_zone"]
            for value, label, color in (
                ((entry_low + entry_high) / 2, "OB midpoint", "#00C878"),
                (recommendation["stop_loss"], "Indicative SL", "#F04646"),
                (recommendation["take_profit"], "Indicative 2R target", "#4ACBFF"),
            ):
                fig.add_hline(
                    y=value,
                    line_dash="dash",
                    line_color=color,
                    annotation_text=label,
                    row=row_index,
                    col=1,
                )

    title = (
        f"{symbol} Multi-Timeframe SMC Analysis "
        f"· {entry_timeframe} entry context"
    )
    return _style_layout(fig, title, height=max(650, len(timeframes) * 300))
