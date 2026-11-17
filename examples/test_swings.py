import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import matplotlib.pyplot as plt

from mt5_connect import connect, shutdown
from mt5_data import get_multi_tf_data
from strategy import detect_swings


def main():

    if not connect():
        print("MT5 connection failed")
        return

    try:
        tf_data = get_multi_tf_data("EURUSD")

        df = tf_data["ltf"]

        swings = detect_swings(df, window=2)

        swing_highs = swings[swings["type"] == "high"]
        swing_lows = swings[swings["type"] == "low"]

        plt.figure(figsize=(18, 8))

        plt.plot(df.index, df["close"], label="Close Price")

        plt.scatter(
            swing_highs["index"],
            swing_highs["price"],
            marker="^",
            s=100,
            label="Swing High"
        )

        plt.scatter(
            swing_lows["index"],
            swing_lows["price"],
            marker="v",
            s=100,
            label="Swing Low"
        )

        plt.title("SMC Swing Detection Validation")
        plt.legend()
        plt.grid(True)

        plt.show()

    finally:
        shutdown()


if __name__ == "__main__":
    main()