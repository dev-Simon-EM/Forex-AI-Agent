"""Rule-based market analyzer using SMC (Smart Money Concepts) signals.

Functions:
- analyze_market(market_input: str, context: str = "") -> str

Returns a structured trade analysis with bias, confidence, entry, stop loss, take profit, and risk/reward ratio.
"""


def analyze_market(market_input, context=""):
    """Analyze market using rule-based SMC signals.
    
    Args:
        market_input (str): Market description (e.g., "uptrend, bos detected")
        context (str): Retrieved SMC knowledge context
    
    Returns:
        str: Formatted trade setup analysis
    """
    text = (str(market_input) + " " + str(context)).lower()

    bias = "Neutral"
    reasons = []
    score = 0

    entry = "Not defined"
    sl = "Not defined"
    tp = "Not defined"
    rr = "Not calculated"

    # =============================
    # SMC SIGNAL DETECTION
    # =============================

    bos = "break of structure" in text or "bos" in text
    choch = "choch" in text or "change of character" in text
    liquidity = "liquidity sweep" in text or "grabbed liquidity" in text
    ob = "order block" in text or "ob" in text

    uptrend = "uptrend" in text or "higher high" in text
    downtrend = "downtrend" in text or "lower high" in text

    # =============================
    # BIAS + SCORE
    # =============================

    if bos:
        bias = "Bullish"
        score += 35
        reasons.append("Break of Structure detected")

    if choch:
        bias = "Bullish"
        score += 30
        reasons.append("CHoCH confirms potential reversal/continuation")

    if liquidity:
        score += 25
        reasons.append("Liquidity sweep detected")

    if ob:
        score += 20
        reasons.append("Order block identified")

    if downtrend:
        bias = "Bearish"
        score += 25
        reasons.append("Bearish structure (lower highs)")

    if uptrend:
        bias = "Bullish"
        score += 25
        reasons.append("Bullish structure (higher highs)")

    if score == 0:
        bias = "Neutral"
        reasons.append("No valid SMC setup")
        score = -30

    confidence = max(0, min(100, score))

    # =============================
    # ENTRY SYSTEM LOGIC
    # =============================

    if bias == "Bullish":
        entry = "Buy zone (Order Block / Demand Area)"
        sl = "Below liquidity sweep / recent swing low"
        tp = "Next liquidity high / previous resistance"
        rr = "1:2 or better"

    elif bias == "Bearish":
        entry = "Sell zone (Order Block / Supply Area)"
        sl = "Above liquidity sweep / recent swing high"
        tp = "Next liquidity low / previous support"
        rr = "1:2 or better"

    else:
        entry = "No clear entry"
        sl = "N/A"
        tp = "N/A"
        rr = "N/A"

    # =============================
    # OUTPUT
    # =============================

    result = f"""
==============================
FOREX AI TRADE SETUP (SMC RULES)
==============================

📊 Market Bias: {bias}
🎯 Confidence Score: {confidence}%

📍 Key Observations:
"""

    for r in reasons:
        result += f"  • {r}\n"

    result += f"""
------------------------------
📌 TRADE SETUP
------------------------------

📍 Entry: {entry}
🛑 Stop Loss: {sl}
🎯 Take Profit: {tp}
⚖️ Risk/Reward: {rr}

------------------------------
💡 Trade Plan:
  • Wait for confirmation on lower timeframe (M5/M15)
  • Enter only if price respects entry zone
  • Avoid trading during uncertainty

⚠️ Risk Management:
  • Risk only 1–2% per trade
  • Do not overtrade
  • Stick to setup rules

📌 Disclaimer:
Educational tool only — not financial advice.
==============================
"""

    return result
