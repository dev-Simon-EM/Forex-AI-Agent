def calculate_lot_size(balance: float, risk_percent: float, entry: float, stop_loss: float) -> float:
    """Calculate lot size based on balance, risk percentage, and stop loss distance."""
    risk_amount = balance * (risk_percent / 100)
    
    # Calculate pip distance (assuming 5-digit broker)
    pip_distance = abs(entry - stop_loss) * 100000  # Convert to pips
    
    if pip_distance == 0:
        return 0.0
    
    # Simple forex lot size formula: lot_size = risk_amount / (pip_distance * pip_value)
    # Assuming pip_value = 10 USD per pip for EURUSD with 1 lot
    pip_value_per_lot = 10.0
    lot_size = risk_amount / (pip_distance * pip_value_per_lot)
    
    return round(lot_size, 2)


def calculate_rr(entry: float, stop_loss: float, take_profit: float) -> float:
    """Calculate risk-reward ratio."""
    risk = abs(entry - stop_loss)
    reward = abs(take_profit - entry)
    
    if risk == 0:
        return 0.0
    
    return round(reward / risk, 2)