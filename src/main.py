import pandas as pd
import requests
from binance.client import Client
import time
import os
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
client = Client(API_KEY, API_SECRET)



# Fetch Historical Data
def fetch_data(symbol, interval, limit=100):
    """Fetch historical data from Binance."""
    candles = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                        'quote_asset_volume', 'num_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df['close'] = pd.to_numeric(df['close'])
    return df[['time', 'close']]

# Calculate EMA
def calculate_ema(df, span):
    """Calculate Exponential Moving Average."""
    return df['close'].ewm(span=span, adjust=False).mean()

# Telegram Alert
def send_telegram_message(message):
    """Send a message to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"  # Optional: Enables HTML formatting
    }
    response = requests.post(url, json=payload)
    return response.json()

# Generate Binance Chart Link
def binance_chart_link(symbol, interval):
    """Generate a Binance chart link."""
    symbol_pair = symbol.split('USDT')[0]  # Assuming USDT pairs
    return f"https://www.binance.com/en-IN/trade/{symbol_pair}_USDT?type=spot&tradePair={symbol}&view=spot&symbol={symbol}&interval={interval.lower()}"

# Trigger Alerts
def trigger_alert(signal, symbol, price, interval, df):
    """Send buy/sell alerts via Telegram."""
    chart_link = binance_chart_link(symbol, interval)
    message = None
    
    if signal == "BUY":
        message = f"🚀 <b>Buy Alert</b> for {symbol} ({interval})!\nPrice: {price:.2f}\n📈 <a href='{chart_link}'>View Chart</a>"
    elif signal == "SELL":
        message = f"🔻 <b>Sell Alert</b> for {symbol} ({interval})!\nPrice: {price:.2f}\n📉 <a href='{chart_link}'>View Chart</a>"
    
    if message:
        # Send message to Telegram
        response = send_telegram_message(message)
        print(f"Telegram response: {response}")
        
        # Update dataframe to avoid duplicate alerts
        df.loc[df.index, 'alert_sent'] = True
    return df

# Check for Buy/Sell Signals
def check_signals(df, symbol, interval):
    """Check for buy/sell signals and send Telegram alerts."""
    df['ema_9'] = calculate_ema(df, 9)
    df['ema_20'] = calculate_ema(df, 20)
    df['signal'] = None
    df['alert_sent'] = False

    for i in range(1, len(df)):
        # Crossover logic
        if df['ema_9'].iloc[i] > df['ema_20'].iloc[i] and df['ema_9'].iloc[i - 1] <= df['ema_20'].iloc[i - 1]:
            if df['close'].iloc[i] > df['close'].iloc[i - 1] and not df['alert_sent'].iloc[i]:
                df = trigger_alert('BUY', symbol, df['close'].iloc[i], interval, df)
        elif df['ema_9'].iloc[i] < df['ema_20'].iloc[i] and df['ema_9'].iloc[i - 1] >= df['ema_20'].iloc[i - 1]:
            if df['close'].iloc[i] < df['close'].iloc[i - 1] and not df['alert_sent'].iloc[i]:
                df = trigger_alert('SELL', symbol, df['close'].iloc[i], interval, df)
    return df

# Monitor Multiple Pairs and Intervals
def monitor_pairs():
    """Monitor multiple pairs and intervals."""
    pairs = ["BTCUSDT", "ETHUSDT"]  # Pairs to monitor
    intervals = ["15m", "1h"]  # Timeframes to monitor
    
    while True:
        for pair in pairs:
            for interval in intervals:
                try:
                    print(f"Fetching data for {pair} at {interval}...")
                    data = fetch_data(pair, interval)
                    print(f"Checking signals for {pair} at {interval}...")
                    data = check_signals(data, pair, interval)
                except Exception as e:
                    print(f"Error monitoring {pair} at {interval}: {e}")
        
        # Sleep for a specified interval (e.g., 5 minutes)
        time.sleep(300)

# Main Function
if __name__ == "__main__":
    monitor_pairs()


