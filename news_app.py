from flask import Flask, render_template, request
import requests

app = Flask(__name__)

# TODO: Add your MarketAux API token here
API_TOKEN = "9PttxLoCRjWeY7qwq75ueJgI1eQd9G018vBWi9XD"
API_URL = "https://api.marketaux.com/v1/news/all"

def get_news(symbols=None):
    """
    Fetches news from the MarketAux API or returns mock data if no API token is provided.
    """
    if API_TOKEN == "YOUR_API_TOKEN_HERE":
        print("Using mock data because API token is not set.")
        # Return mock data if the API token is not set
        return [
            {
                'title': 'Tesla Stock Surges on New Model Announcement',
                'description': 'Tesla shares jumped over 5% after the company unveiled its new, more affordable electric vehicle.',
                'url': '#',
                'source': 'fakenews.com'
            },
            {
                'title': 'Apple Reports Record Profits in Q4',
                'description': 'Apple announced record-breaking fourth-quarter earnings, driven by strong iPhone sales.',
                'url': '#',
                'source': 'techcrunch-mock.com'
            },
            {
                'title': 'Market Hits All-Time High Amidst Economic Recovery',
                'description': 'The S&P 500 reached a new peak today as investors are optimistic about the economic outlook.',
                'url': '#',
                'source': 'reuters-mock.com'
            }
        ]

    params = {
        'api_token': API_TOKEN,
        'language': 'en',
    }
    if symbols:
        params['symbols'] = symbols

    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json().get('data', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")
        return []

@app.route('/', methods=['GET', 'POST'])
def index():
    news = []
    if request.method == 'POST':
        symbols = request.form.get('symbols')
        news = get_news(symbols)
    else:
        news = get_news()

    return render_template('index.html', news=news)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)