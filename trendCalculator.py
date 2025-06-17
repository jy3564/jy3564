import pandas as pd
import numpy as np

def get_trend(close_series: pd.Series, short_window: int, medium_window: int, long_window: int) -> str:
    """
    Calculates the trend based on Simple Moving Averages (SMAs) of different periods.
    :param close_series: A pandas Series of closing prices.
    :param short_window: The window period for the short-term SMA.
    :param medium_window: The window period for the medium-term SMA.
    :param long_window: The window period for the long-term SMA.
    :return: "UPTREND", "DOWNTREND", or "SIDEWAYS/UNCERTAIN" signal.
    """
    if close_series is None or len(close_series) < long_window:
        return "SIDEWAYS/UNCERTAIN"

    try:
        sma_short = close_series.rolling(window=short_window).mean().iloc[-1]
        sma_medium = close_series.rolling(window=medium_window).mean().iloc[-1]
        sma_long = close_series.rolling(window=long_window).mean().iloc[-1]
    except IndexError: # Can happen if series is shorter than window after NaNs are dropped by rolling
        return "SIDEWAYS/UNCERTAIN"
    except Exception: # Catch any other potential error during SMA calculation
        return "SIDEWAYS/UNCERTAIN"


    if pd.isna(sma_short) or pd.isna(sma_medium) or pd.isna(sma_long):
        return "SIDEWAYS/UNCERTAIN"

    if sma_short > sma_medium and sma_medium > sma_long: # Added 'and' for clarity
        return "UPTREND"
    elif sma_short < sma_medium and sma_medium < sma_long: # Added 'and' for clarity
        return "DOWNTREND"
    else:
        return "SIDEWAYS/UNCERTAIN"

if __name__ == '__main__':
    data_up = pd.Series([i + (j*0.1) for i, j in enumerate(range(10, 70))]) # 60 data points
    print(f"Trend for data_up (len {len(data_up)}): {get_trend(data_up, 5, 10, 20)}")

    data_down = pd.Series([70 - i - (j*0.1) for i, j in enumerate(range(10, 70))])
    print(f"Trend for data_down (len {len(data_down)}): {get_trend(data_down, 5, 10, 20)}")

    data_sideways_raw = [50, 51, 50, 52, 50, 53, 50, 54, 50, 55, 50, 54, 50, 53, 50, 52, 50, 51, 50, 49, 50, 48, 50, 47, 50]
    data_sideways = pd.Series(data_sideways_raw * 3) # Ensure it's long enough
    print(f"Trend for data_sideways (len {len(data_sideways)}): {get_trend(data_sideways, 5, 10, 20)}")

    data_short = pd.Series([10.0,11.0,12.0,13.0,14.0,15.0]) # Not long enough for window 20
    print(f"Trend for data_short (len {len(data_short)}): {get_trend(data_short, 5, 10, 20)}")

    data_with_nans = pd.Series([10.0, 11.0, np.nan, 13.0, 14.0] * 5) # Has NaNs
    print(f"Trend for data_with_nans (len {len(data_with_nans)}): {get_trend(data_with_nans, 3, 5, 8)}")
