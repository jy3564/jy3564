def get_rsi_signal(current_rsi_value: float, rsi_buy_threshold: float = 30, rsi_sell_threshold: float = 70):
    """
    Determines a signal based on the current RSI value and thresholds.
    :param current_rsi_value: The current RSI value.
    :param rsi_buy_threshold: RSI level below which is considered oversold.
    :param rsi_sell_threshold: RSI level above which is considered overbought.
    :return: "BUY", "SELL", or "HOLD" signal.
    """
    signal = "HOLD"
    if current_rsi_value < rsi_buy_threshold:
        signal = "BUY" # Oversold
    elif current_rsi_value > rsi_sell_threshold:
        signal = "SELL" # Overbought
    return signal

if __name__ == '__main__':
    print(f"RSI Signal (25): {get_rsi_signal(25)}")
    print(f"RSI Signal (75): {get_rsi_signal(75)}")
    print(f"RSI Signal (50): {get_rsi_signal(50)}")
