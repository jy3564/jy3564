from collections import deque

def get_macd_signal(current_macd_line: float, current_signal_line: float, current_histogram: float, macd_history: deque = None):
    """
    Determines a signal based on MACD values.
    :param current_macd_line: The current MACD line value.
    :param current_signal_line: The current MACD signal line value.
    :param current_histogram: The current MACD histogram value (macd_line - signal_line).
    :param macd_history: Optional deque of recent MACD data points (e.g., previous histogram values).
    :return: "BUY", "SELL", or "HOLD" signal.
    """
    signal = "HOLD"

    if macd_history and len(macd_history) > 0:
        prev_histogram = macd_history[-1]

        if current_histogram > 0 and prev_histogram <= 0:
            signal = "BUY"
        elif current_histogram < 0 and prev_histogram >= 0:
            signal = "SELL"

    return signal

if __name__ == '__main__':
    history = deque(maxlen=5)

    history.append(-0.1)
    print(f"MACD Signal (PrevHist: -0.1, CurrHist: 0.2): {get_macd_signal(0.5, 0.3, 0.2, history)}")

    history.clear()
    history.append(0.15)
    print(f"MACD Signal (PrevHist: 0.15, CurrHist: -0.2): {get_macd_signal(-0.4, -0.2, -0.2, history)}")

    history.clear()
    history.append(0.1)
    print(f"MACD Signal (PrevHist: 0.1, CurrHist: 0.2): {get_macd_signal(0.6, 0.4, 0.2, history)}")
