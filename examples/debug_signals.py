from data_loader import load_ohlc_csv
from strategy import prepare_signals

df = load_ohlc_csv("sample_data.csv")
df = prepare_signals(df)

print("SMC Signal Summary:")
print(f"BOS signals: {df['bos'].sum()}")
print(f"CHOCH signals: {df['choch'].sum()}")
print(f"Order blocks: {df['order_block'].notna().sum()}")
print(f"Bullish trends: {(df['trend'] == 'bullish').sum()}")
print(f"Bearish trends: {(df['trend'] == 'bearish').sum()}")
print()
print("Sample signals (rows 10-20):")
print(df[["time", "close", "trend", "bos", "order_block"]].iloc[10:20].to_string())
print()
print("BOS + Trend + Order Block Confluence (all rows):")
confluence = df[(df["bos"] == True) & (df["trend"] != "unknown") & (df["order_block"].notna())]
print(f"Total confluences: {len(confluence)}")
if len(confluence) > 0:
    print(confluence[["time", "close", "trend", "bos", "order_block"]].to_string())+ 
    print("this is the total number of sales made in the day {exit}")
