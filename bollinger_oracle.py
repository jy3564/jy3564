import pandas as pd
from collections import deque

def get_bollinger_band_signal(current_price: float, bb_upper: float, bb_lower: float, bb_middle: float, bollinger_history: deque = None):
    """
    Determines a signal based on Bollinger Bands.
    :param current_price: The current price of the asset.
    :param bb_upper: Current upper Bollinger Band.
    :param bb_lower: Current lower Bollinger Band.
    :param bb_middle: Current middle Bollinger Band (SMA).
    :param bollinger_history: Optional deque of recent Bollinger Band values or price relation to bands.
    :return: "BUY", "SELL", or "HOLD" signal.
    """
    signal = "HOLD"
    if current_price < bb_lower:
        signal = "BUY"
    elif current_price > bb_upper:
        signal = "SELL"
    return signal

if __name__ == '__main__':
    price = 90.0
    upper = 105.0
    lower = 95.0
    middle = 100.0
    print(f"Bollinger Signal (Price: {price}, Bands L/M/U: {lower}/{middle}/{upper}): {get_bollinger_band_signal(price, upper, lower, middle)}")

    price = 110.0
    print(f"Bollinger Signal (Price: {price}, Bands L/M/U: {lower}/{middle}/{upper}): {get_bollinger_band_signal(price, upper, lower, middle)}")

    price = 100.0
    print(f"Bollinger Signal (Price: {price}, Bands L/M/U: {lower}/{middle}/{upper}): {get_bollinger_band_signal(price, upper, lower, middle)}")
