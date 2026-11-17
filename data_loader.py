import pandas as pd


def load_data(csv_path: str) -> pd.DataFrame:
    """
    Load OHLC data from a CSV file and standardize it for SMC analysis.
    Expected columns: time, open, high, low, close (volume optional)
    """

    df = pd.read_csv(csv_path)

    # Standardize column names
    df.columns = [col.strip().lower() for col in df.columns]

    # Required columns check
    required = {"time", "open", "high", "low", "close"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Clean time column
    df["time"] = df["time"].astype(str).str.replace(" UTC", "", regex=False)

    # Convert time safely (handles most forex CSV formats)
    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    # Remove invalid timestamps
    df = df.dropna(subset=["time"])

    # Sort chronologically
    df = df.sort_values("time").reset_index(drop=True)

    return df


def validate_dataframe(df: pd.DataFrame) -> bool:
    """
    Quick validator for SMC pipeline safety.
    """
    required = {"time", "open", "high", "low", "close"}
    return required.issubset(df.columns)


def load_ohlc_csv(csv_path: str) -> pd.DataFrame:
    """Compatibility entry point used by the backtest command."""
    return load_data(csv_path)