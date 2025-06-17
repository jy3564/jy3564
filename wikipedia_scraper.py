import requests
import pandas as pd
from bs4 import BeautifulSoup
import io

def get_sp500_nasdaq_100_symbols(
    sp500_url: str = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    nasdaq100_url: str = "https://en.wikipedia.org/wiki/Nasdaq-100"
    ):
    """
    Fetches S&P 500 and Nasdaq-100 stock symbols from Wikipedia,
    combines them, removes duplicates, and returns a sorted list.

    :param sp500_url: URL for the S&P 500 list.
    :param nasdaq100_url: URL for the Nasdaq-100 list.
    :return: A sorted list of unique stock symbols.
    """
    symbols = set()

    # S&P 500
    # sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies" # Now an argument
    try:
        print(f"Fetching S&P 500 symbols from {sp500_url}...")
        response = requests.get(sp500_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        sp500_tables = pd.read_html(io.StringIO(response.text), attrs={'id': 'constituents'})
        if sp500_tables:
            sp500_df = sp500_tables[0]
            if 'Symbol' in sp500_df.columns:
                symbols.update(sp500_df['Symbol'].str.replace('.', '-', regex=False).tolist())
                print(f"Found {len(sp500_df['Symbol'])} S&P 500 symbols.")
            else:
                print("Error: 'Symbol' column not found in S&P 500 table.")
        else:
            print("Error: S&P 500 constituents table not found.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching S&P 500 data: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while parsing S&P 500 data: {e}")

    # Nasdaq-100
    # nasdaq100_url = "https://en.wikipedia.org/wiki/Nasdaq-100" # Now an argument
    try:
        print(f"\nFetching Nasdaq-100 symbols from {nasdaq100_url}...")
        response = requests.get(nasdaq100_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        nasdaq_df = None

        components_header_span = soup.find('span', id='Components')
        if components_header_span:
            print("Found 'Components' span for Nasdaq-100.")
            parent_element = components_header_span.parent
            table_element = None
            if parent_element:
                table_element = parent_element.find_next_sibling('table')
            if not table_element:
                table_element = components_header_span.find_next('table')

            if table_element:
                nasdaq_tables_list = pd.read_html(io.StringIO(str(table_element)))
                if nasdaq_tables_list:
                    temp_df = nasdaq_tables_list[0]
                    if 'Ticker' in temp_df.columns:
                        nasdaq_df = temp_df
                        symbols.update(nasdaq_df['Ticker'].str.replace('.', '-', regex=False).tolist())
                        print(f"Found {len(nasdaq_df['Ticker'])} Nasdaq-100 symbols using primary method.")
                    # ... (rest of primary method error handling)
            # ... (rest of primary method error handling)
        else:
            print("Primary method: 'Components' header span not found for Nasdaq-100.")

        if nasdaq_df is None: # Fallback if primary failed
            print("Attempting fallback for Nasdaq-100: Searching for table by id='constituents'...")
            try:
                nasdaq_tables_fallback = pd.read_html(io.StringIO(response.text), attrs={'id': 'constituents'})
                if nasdaq_tables_fallback:
                    nasdaq_df_fallback = nasdaq_tables_fallback[0]
                    if 'Ticker' in nasdaq_df_fallback.columns:
                        nasdaq_df = nasdaq_df_fallback
                        symbols.update(nasdaq_df['Ticker'].str.replace('.', '-', regex=False).tolist())
                        print(f"Found {len(nasdaq_df['Ticker'])} Nasdaq-100 symbols using fallback (id='constituents').")
                    else:
                        print("Error (Fallback): 'Ticker' column not found in Nasdaq-100 table with id='constituents'.")
                else:
                    print("Error (Fallback): Nasdaq-100 constituents table (id='constituents') not found.")
            except Exception as e_fallback:
                print(f"Error (Fallback): Exception during Nasdaq-100 fallback: {e_fallback}")

        if nasdaq_df is None:
             print("\nError: Nasdaq-100 symbols could not be retrieved by any method.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Nasdaq-100 data: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while parsing Nasdaq-100 data: {e}")

    return sorted(list(set(s for s in symbols if s and isinstance(s, str)))) # Added set for final dedupe and type check


if __name__ == '__main__':
    stock_symbols = get_sp500_nasdaq100_symbols()
    if stock_symbols:
        print(f"\nFound {len(stock_symbols)} unique symbols in total.")
        # print(stock_symbols)
    else:
        print("\nNo symbols found or an error occurred.")
