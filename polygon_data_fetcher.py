import os
import pandas as pd
import requests # For requests.exceptions.HTTPError
from polygon import RESTClient

def fetch_stock_data(api_key: str, ticker: str, start_date: str, end_date: str, multiplier: int = 1, timespan: str = 'day', adjusted: bool = True, sort: str = 'asc', limit: int = 5000) -> pd.DataFrame:
    """
    Fetches historical stock data using the polygon.io API.
    """
    try:
        client = RESTClient(api_key)
        aggs_list = []
        print(f"Fetching data for {ticker} from {start_date} to {end_date} with timespan {multiplier} {timespan}...")
        for agg in client.list_aggs(
            ticker=ticker,
            multiplier=multiplier,
            timespan=timespan,
            from_=start_date,
            to=end_date,
            adjusted=adjusted,
            sort=sort,
            limit=limit,
        ):
            aggs_list.append(agg)

        if not aggs_list:
            print(f"No data found for {ticker} from {start_date} to {end_date} with the given parameters via polygon.io.")
            return pd.DataFrame()

        print(f"Successfully fetched {len(aggs_list)} aggregate(s) for {ticker} from polygon.io.")
        df = pd.DataFrame([
            {
                'timestamp': agg.timestamp, 'open': agg.open, 'high': agg.high, 'low': agg.low,
                'close': agg.close, 'volume': agg.volume, 'vwap': getattr(agg, 'vwap', None),
                'transactions': getattr(agg, 'transactions', None),
            } for agg in aggs_list
        ])
        expected_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'vwap', 'transactions']
        for col in expected_cols:
            if col not in df.columns: df[col] = pd.NA
        df = df[expected_cols]
        if 'timestamp' in df.columns and not df['timestamp'].empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        if not df.empty and 'timestamp' in df.columns:
            df = df.sort_values(by='timestamp').reset_index(drop=True)
        return df
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error for {ticker}: {e}")
        if e.response is not None: print(f"Status: {e.response.status_code}, Content: {e.response.text[:200]}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Unexpected error for {ticker}: {e}")
        return pd.DataFrame()

if __name__ == '__main__':
    print("Polygon Data Fetcher module direct execution test.")
    # Minimal test to avoid issues with the end of the file.
    # Actual testing of fetch_stock_data is done via run_selector.py or dedicated tests.
    pass
```
