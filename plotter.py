import logging
from typing import Dict

import pandas as pd
import plotly.graph_objects as go

from smc.detection import generate_smc_signal_frame
from strategy import detect_swings

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


def _get_half_bar_width(df: pd.DataFrame) -> pd.Timedelta:
    if len(df) < 2:
        return pd.Timedelta(minutes=1)
    delta = df["time"].diff().median()
    return delta / 2 if pd.notna(delta) and delta > pd.Timedelta(0) else pd.Timedelta(minutes=1)


def _style_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=title,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        height=720,
        plot_bgcolor="#0f0f15",
        paper_bgcolor="#0f0f15",
        legend=dict(bgcolor="rgba(0,0,0,0.35)", orientation="h", y=1.02, x=0),
        margin=dict(l=50, r=30, t=80, b=50),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#222", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#222", zeroline=False)
    return fig


def _add_swing_markers(fig: go.Figure, df: pd.DataFrame, swings: pd.DataFrame) -> None:
    if swings.empty:
        return

    highs = swings[swings["type"] == "high"]
    lows = swings[swings["type"] == "low"]

    if not highs.empty:
        fig.add_trace(
            go.Scatter(
                x=df.loc[highs["index"], "time"],
                y=highs["price"],
                mode="markers",
                marker=dict(symbol="triangle-down", color="#FF7F50", size=12),
                name="Swing High",
            )
        )

    if not lows.empty:
        fig.add_trace(
            go.Scatter(
                x=df.loc[lows["index"], "time"],
                y=lows["price"],
                mode="markers",
                marker=dict(symbol="triangle-up", color="#7CFC00", size=12),
                name="Swing Low",
            )
        )


def _add_bos_shapes(fig: go.Figure, df: pd.DataFrame, signals: pd.DataFrame) -> None:
    if signals.empty:
        return

    for index, row in signals[signals["bos"]].iterrows():
        if row["bias"] not in {"bullish", "bearish"}:
            continue

        current_index = int(index)
        window = df.loc[max(0, current_index - 5) : current_index - 1]
        if window.empty:
            continue

        if row["bias"] == "bullish":
            level = window["high"].max()
            color = "#FF4500"
            annotation = "BOS bullish"
            marker_symbol = "star-triangle-up"
        else:
            level = window["low"].min()
            color = "#00BFFF"
            annotation = "BOS bearish"
            marker_symbol = "star-triangle-down"

        fig.add_hline(
            y=level,
            line_dash="dash",
            line_color=color,
            annotation_text=annotation,
            annotation_position="bottom right",
            opacity=0.8,
        )
        fig.add_trace(
            go.Scatter(
                x=[row["time"]],
                y=[df.at[current_index, "close"]],
                mode="markers",
                marker=dict(symbol=marker_symbol, size=14, color=color),
                name=f"BOS point ({row['bias']})",
            )
        )


def _add_choch_annotations(fig: go.Figure, df: pd.DataFrame, signals: pd.DataFrame) -> None:
    if signals.empty:
        return

    for _, row in signals[signals["choch"]].iterrows():
        position = int(row.name)
        y = df.at[position, "high"] * 1.002 if row["bias"] == "bullish" else df.at[position, "low"] * 0.998
        fig.add_annotation(
            x=row["time"],
            y=y,
            text="CHOCH",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-30 if row["bias"] == "bullish" else 30,
            font=dict(color="#F5DEB3", size=12),
            bgcolor="rgba(0,0,0,0.65)",
            bordercolor="#777",
        )


def _add_liquidity_zones(fig: go.Figure, df: pd.DataFrame, signals: pd.DataFrame, half_width: pd.Timedelta) -> None:
    liquidity_signals = signals[signals["liquidity_zone"].notna()]
    if liquidity_signals.empty:
        return

    for _, row in liquidity_signals.iterrows():
        position = int(row.name)
        time = row["time"]
        if row["liquidity_zone"] == "equal_highs":
            top = df.at[position, "high"] * 1.0006
            bottom = df.at[position, "high"] * 0.9990
            zone_color = "rgba(255,165,0,0.18)"
            label = "Liquidity Highs"
        else:
            top = df.at[position, "low"] * 1.0010
            bottom = df.at[position, "low"] * 0.9992
            zone_color = "rgba(135,206,235,0.18)"
            label = "Liquidity Lows"

        fig.add_shape(
            type="rect",
            xref="x",
            yref="y",
            x0=time - half_width,
            x1=time + half_width,
            y0=bottom,
            y1=top,
            fillcolor=zone_color,
            line=dict(width=0),
            layer="below",
        )
        fig.add_annotation(
            x=time,
            y=top,
            text=label,
            showarrow=False,
            yshift=8,
            font=dict(color="#FFFFFF", size=11),
            bgcolor="rgba(0,0,0,0.4)",
        )


def _add_order_block_shapes(fig: go.Figure, signals: pd.DataFrame, half_width: pd.Timedelta) -> None:
    for _, row in signals[signals["order_block"].notna()].iterrows():
        order_block = row["order_block"]
        if not isinstance(order_block, dict):
            continue

        time = order_block.get("start_time", row["time"])
        low = order_block["low"]
        high = order_block["high"]
        block_color = "rgba(0,255,0,0.18)" if order_block["type"] == "bullish" else "rgba(255,0,0,0.18)"

        fig.add_shape(
            type="rect",
            xref="x",
            yref="y",
            x0=time - half_width,
            x1=time + half_width,
            y0=low,
            y1=high,
            fillcolor=block_color,
            line=dict(color=block_color, width=1),
            layer="below",
        )


def plot_trade(df: pd.DataFrame, setup: Dict[str, object]) -> None:
    df = _normalize_ohlc(df)
    signals = generate_smc_signal_frame(df)
    half_width = _get_half_bar_width(df)

    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
            increasing_line_color="#00BFA5",
            decreasing_line_color="#F44336",
        )
    )

    _add_swing_markers(fig, df, detect_swings(df, window=2))
    _add_bos_shapes(fig, df, signals)
    _add_choch_annotations(fig, df, signals)
    _add_liquidity_zones(fig, df, signals, half_width)
    _add_order_block_shapes(fig, signals, half_width)

    if setup.get("entry") is not None:
        fig.add_hline(
            y=setup["entry"],
            line_dash="dash",
            line_color="#00FF9D",
            annotation_text=f"Entry {setup['entry']:.5f}",
            annotation_position="bottom right",
        )
    if setup.get("stop_loss") is not None:
        fig.add_hline(
            y=setup["stop_loss"],
            line_dash="dot",
            line_color="#FF4D4D",
            annotation_text=f"SL {setup['stop_loss']:.5f}",
            annotation_position="top right",
        )
    if setup.get("take_profit") is not None:
        fig.add_hline(
            y=setup["take_profit"],
            line_dash="dot",
            line_color="#4ACBFF",
            annotation_text=f"TP {setup['take_profit']:.5f}",
            annotation_position="top left",
        )

    metadata = f"Bias: {setup.get('bias', 'neutral').title()} | RR: {setup.get('rr', 'N/A')} | Confidence: {setup.get('confidence', 0):.0f}%"
    fig.add_annotation(
        text=metadata,
        xref="paper",
        yref="paper",
        x=0,
        y=1.05,
        showarrow=False,
        font=dict(size=13, color="#FFFFFF"),
        bgcolor="rgba(0,0,0,0.4)",
        bordercolor="#444",
    )

    fig = _style_layout(fig, f"SMC Trade Setup — {setup.get('bias', 'Neutral').title()}")
    fig.update_xaxes(title_text="Time")
    fig.update_yaxes(title_text="Price")

    fig.show()
