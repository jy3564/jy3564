import pandas as pd
from datetime import datetime, timedelta
import time # For potential rate limiting

# Import project modules
import config_manager
import wikipedia_scraper
import polygon_data_fetcher
import stock_selector_core
import html_reporter

def run_analysis():
    """
    Main function to run the stock selection and analysis process.
    """
    print("Starting stock analysis run...")

    # --- 0. Load Configuration ---
    try:
        config = config_manager.load_config("config.yaml")
        if not config:
            print("Configuration could not be loaded. Exiting.")
            return
        print("Configuration loaded successfully.")
    except Exception as e:
        print(f"Error loading configuration: {e}. Exiting.")
        return

    # --- Configuration from Loaded Config ---
    API_KEY = config.get('api_keys', {}).get('polygon', "YOUR_POLYGON_API_KEY_FALLBACK")

    # Data fetching parameters
    df_config = config.get('data_fetching', {})
    # Determine if using daily or intraday settings based on a primary config or default
    # For this example, let's assume a 'current_run_type' could be in config, or default to daily
    run_type = df_config.get('run_type', 'daily') # Example: add 'run_type: daily' or 'run_type: intraday' to config

    if run_type == 'intraday':
        start_offset = df_config.get('intraday_start_date_offset_days', 7)
        MULTIPLIER = df_config.get('intraday_timespan_multiplier', 5)
        TIMESPAN = df_config.get('intraday_timespan_unit', "minute")
    else: # Default to daily
        start_offset = df_config.get('start_date_offset_days', 180)
        MULTIPLIER = df_config.get('daily_timespan_multiplier', 1)
        TIMESPAN = df_config.get('daily_timespan_unit', "day")

    END_DATE = (datetime.now() - timedelta(days=df_config.get('end_date_offset_days', 0))).strftime("%Y-%m-%d")
    START_DATE = (datetime.now() - timedelta(days=start_offset)).strftime("%Y-%m-%d")
    ADJUSTED_OHLC = df_config.get('adjusted_ohlc', True)
    API_LIMIT = df_config.get('api_limit_per_call', 5000)

    # Stock universe
    uni_config = config.get('stock_universe', {})
    USE_WIKIPEDIA_SCRAPER = uni_config.get('use_wikipedia_scraper', True)
    SP500_URL = uni_config.get('sp500_url', "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    NASDAQ100_URL = uni_config.get('nasdaq100_url', "https://en.wikipedia.org/wiki/Nasdaq-100")
    # MANUAL_SYMBOLS = uni_config.get('manual_symbol_list', []) # If using manual list

    # Application settings
    app_config = config.get('application', {})
    MAX_SYMBOLS = app_config.get('max_symbols_to_process', 0) # 0 or negative for all

    # Reporting
    report_config = config.get('reporting', {})
    REPORT_FILENAME = report_config.get('report_filename', "trading_signals_report.html")


    print(f"Run Parameters: API_KEY_SET={'YES' if API_KEY not in ['YOUR_POLYGON_API_KEY', 'YOUR_POLYGON_API_KEY_FALLBACK'] else 'NO (Placeholder In Use!)'}, "
          f"START_DATE={START_DATE}, END_DATE={END_DATE}, TIMESPAN={MULTIPLIER} {TIMESPAN}, MaxSymbols={MAX_SYMBOLS if MAX_SYMBOLS > 0 else 'ALL'}")

    if API_KEY in ["YOUR_POLYGON_API_KEY", "YOUR_POLYGON_API_KEY_FALLBACK"]:
        print("\n" + "="*80)
        print("WARNING: Using a placeholder API key for Polygon.io.")
        print("Data fetching will likely fail. Please update API_KEY in config.yaml or environment.")
        print("="*80 + "\n")

    # --- 1. Fetch Stock Universe ---
    symbols = []
    if USE_WIKIPEDIA_SCRAPER:
        print("Fetching stock universe from Wikipedia...")
        try:
            # Pass URLs from config to the scraper function
            symbols = wikipedia_scraper.get_sp500_nasdaq_100_symbols(sp500_url=SP500_URL, nasdaq100_url=NASDAQ100_URL)
            if not symbols: print("No symbols fetched from Wikipedia.")
            else: print(f"Successfully fetched {len(symbols)} unique symbols from Wikipedia.")
        except Exception as e:
            print(f"Error fetching symbols from Wikipedia: {e}")
    # if MANUAL_SYMBOLS and not symbols: # Use manual list if scraper failed or not used
    #     print(f"Using manual symbol list: {MANUAL_SYMBOLS}")
    #     symbols = MANUAL_SYMBOLS

    if not symbols:
        print("No symbols available to process. Exiting.")
        return

    if MAX_SYMBOLS > 0 and len(symbols) > MAX_SYMBOLS:
        symbols = symbols[:MAX_SYMBOLS]
        print(f"Processing a slice of {len(symbols)} symbols based on 'max_symbols_to_process' config.")


    # --- 2. Initialize Signal Generator ---
    print("Initializing Stock Signal Generator with strategy parameters from config...")
    strategy_params_config = config.get('strategy_params', {})
    signal_generator = stock_selector_core.StockSignalGenerator(strategy_config=strategy_params_config)
    recommendations = []

    # --- 3. Process Each Symbol ---
    print(f"\nProcessing {len(symbols)} symbols...")
    for i, symbol in enumerate(symbols):
        print(f"\n({i+1}/{len(symbols)}) Processing {symbol}...")
        try:
            data_df = polygon_data_fetcher.fetch_stock_data(
                api_key=API_KEY,
                ticker=symbol,
                start_date=START_DATE,
                end_date=END_DATE,
                multiplier=MULTIPLIER,
                timespan=TIMESPAN,
                adjusted=ADJUSTED_OHLC,
                limit=API_LIMIT
            )

            if data_df is not None and not data_df.empty:
                print(f"Successfully fetched {len(data_df)} data points for {symbol}.")
                # Ensure DataFrame index is datetime for easier processing if not already
                # This is now handled within StockSignalGenerator._calculate_indicators

                signal = signal_generator.generate_signal(symbol, data_df)
                if signal:
                    print(f"Signal generated for {symbol}: {signal['signal_type']} at {signal.get('price_at_signal',0):.2f} (Confidence: {signal['confidence_score']})")
                    recommendations.append(signal)
                else:
                    print(f"No signal generated for {symbol}.")
            else:
                print(f"No data fetched or empty DataFrame for {symbol}.")

        except Exception as e:
            print(f"An error occurred while processing {symbol}: {e}")

        if i < len(symbols) - 1: # Don't sleep after the last symbol
             time.sleep(0.1) # Small delay to be kind to APIs, configurable if needed

    print(f"\nFinished processing all symbols. Total recommendations: {len(recommendations)}")

    # --- 4. Generate HTML Report ---
    print("Generating HTML report...")
    if recommendations:
        html_reporter.generate_html_report(recommendations, REPORT_FILENAME)
        print(f"HTML report generated: {REPORT_FILENAME}")
    else:
        print("No recommendations to report.")

    print("\nStock analysis run completed.")

if __name__ == '__main__':
    run_analysis()
