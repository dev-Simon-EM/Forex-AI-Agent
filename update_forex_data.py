"""Download and update historical EURUSD and GBPUSD M15 data.

This script uses yfinance to fetch the last 3 months of 15-minute OHLC data
for EURUSD=X and GBPUSD=X, appends it to the existing CSV files, removes
duplicate timestamps, sorts by time, and saves the final CSVs with columns:

    time,open,high,low,close
"""

import os

import pandas as pd
import yfinance as yf

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SYMBOL_FILES = {
    "EURUSD=X": "eurusd_m15.csv",
    "GBPUSD=X": "gbpusd_m15.csv",
}

OUTPUT_COLUMNS = ["time", "open", "high", "low", "close"]


def fetch_symbol_data(ticker: str) -> pd.DataFrame:
    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.DateOffset(months=3)

    df = yf.download(
        tickers=ticker,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval="15m",
        progress=False,
        auto_adjust=False,
        threads=True,
    )

    if df.empty:
        raise ValueError(f"No data downloaded for {ticker}")

    df = df[["Open", "High", "Low", "Close"]].copy()
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.reset_index()
    df["time"] = df["Datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})
    return df[OUTPUT_COLUMNS]


def load_existing_csv(path: str) -> pd.DataFrame:
    if not os.path.isfile(path):
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df = pd.read_csv(path)
    df.columns = [col.strip().lower() for col in df.columns]
    if "volume" in df.columns:
        df = df.drop(columns=["volume"])
    missing = [col for col in OUTPUT_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Existing CSV is missing required columns: {missing}")

    df = df[OUTPUT_COLUMNS].copy()
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    df = df.dropna(subset=["time"])
    return df


def combine_and_save(existing: pd.DataFrame, new_data: pd.DataFrame, path: str) -> int:
    new_data["time"] = pd.to_datetime(new_data["time"], utc=True)
    combined = pd.concat([existing, new_data], ignore_index=True)
    combined = combined.drop_duplicates(subset=["time"], keep="last")
    combined = combined.sort_values("time").reset_index(drop=True)
    combined["time"] = combined["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    combined.to_csv(path, index=False, float_format="%.5f")
    return len(combined)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    for ticker, filename in SYMBOL_FILES.items():
        csv_path = os.path.join(DATA_DIR, filename)
        print(f"Updating {ticker} -> {csv_path}")

        existing = load_existing_csv(csv_path)
        new_data = fetch_symbol_data(ticker)

        before = len(existing)
        total = combine_and_save(existing, new_data, csv_path)

        print(f"  existing rows: {before}")
        print(f"  downloaded rows: {len(new_data)}")
        print(f"  final rows: {total}\n")


if __name__ == "__main__":
    main()
