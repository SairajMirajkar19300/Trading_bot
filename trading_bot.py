import os
import time
import ccxt
import pandas as pd
import ta
from dotenv import load_dotenv
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
MARKET_TYPE = 'crypto'  # 'crypto' or 'forex'
TRADING_PAIR_CRYPTO = 'BTC/USDT'
TRADING_PAIR_FOREX = 'EUR_USD'
TIMEFRAME = '1h'
EMA_SHORT = 9
EMA_LONG = 21
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# --- Risk Management Configuration ---
RISK_PER_TRADE_PERCENT = 10.0  # Risk 10% of the account on each trade
STOP_LOSS_PERCENT = 2.0      # 2% stop loss
TAKE_PROFIT_PERCENT = 6.0    # 6% take profit (3:1 Reward-to-Risk)

# --- API Keys (loaded from .env file) ---
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
OANDA_API_KEY = os.getenv('OANDA_API_KEY')
OANDA_ACCOUNT_ID = os.getenv('OANDA_ACCOUNT_ID')

# --- Initialize APIs ---
def initialize_apis():
    """Initializes the APIs for Binance and OANDA."""
    binance = None
    oanda = None

    if MARKET_TYPE == 'crypto':
        binance = ccxt.binance({
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_SECRET_KEY,
            'options': {
                'defaultType': 'future',
            },
        })
        binance.set_sandbox_mode(True)  # Enable testnet
        print("Binance API Initialized in Testnet Mode")

    elif MARKET_TYPE == 'forex':
        oanda = API(access_token=OANDA_API_KEY, environment="practice")
        print("OANDA API Initialized in Practice (Demo) Mode")

    return binance, oanda

# --- Data Fetching ---
def fetch_data(binance, oanda):
    """Fetches historical data for the selected market."""
    if MARKET_TYPE == 'crypto':
        ohlcv = binance.fetch_ohlcv(TRADING_PAIR_CRYPTO, TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    elif MARKET_TYPE == 'forex':
        params = {
            "count": 100,
            "granularity": TIMEFRAME.upper()
        }
        r = instruments.InstrumentsCandles(instrument=TRADING_PAIR_FOREX, params=params)
        oanda.request(r)
        data = []
        for candle in r.response['candles']:
            time = pd.to_datetime(candle['time'])
            volume = candle['volume']
            mid_candle = candle['mid']
            o, h, l, c = float(mid_candle['o']), float(mid_candle['h']), float(mid_candle['l']), float(mid_candle['c'])
            data.append([time, o, h, l, c, volume])
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    return None

# --- Indicator Calculation ---
def calculate_indicators(df):
    """Calculates technical indicators."""
    df['ema_short'] = ta.trend.EMAIndicator(df['close'], window=EMA_SHORT).ema_indicator()
    df['ema_long'] = ta.trend.EMAIndicator(df['close'], window=EMA_LONG).ema_indicator()
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=RSI_PERIOD).rsi()
    macd = ta.trend.MACD(df['close'], window_slow=MACD_SLOW, window_fast=MACD_FAST, window_sign=MACD_SIGNAL)
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    return df

# --- Signal Generation ---
def generate_signal(df):
    """Generates a trading signal based on the strategy."""
    latest = df.iloc[-1]
    signals = {}

    # EMA Crossover Signal
    if latest['ema_short'] > latest['ema_long'] and df.iloc[-2]['ema_short'] <= df.iloc[-2]['ema_long']:
        signals['ema'] = 'buy'
    elif latest['ema_short'] < latest['ema_long'] and df.iloc[-2]['ema_short'] >= df.iloc[-2]['ema_long']:
        signals['ema'] = 'sell'
    else:
        signals['ema'] = 'hold'

    # RSI Signal
    if latest['rsi'] < RSI_OVERSOLD:
        signals['rsi'] = 'buy'
    elif latest['rsi'] > RSI_OVERBOUGHT:
        signals['rsi'] = 'sell'
    else:
        signals['rsi'] = 'hold'

    # MACD Signal
    if latest['macd'] > latest['macd_signal'] and df.iloc[-2]['macd'] <= df.iloc[-2]['macd_signal']:
        signals['macd'] = 'buy'
    elif latest['macd'] < latest['macd_signal'] and df.iloc[-2]['macd'] >= df.iloc[-2]['macd_signal']:
        signals['macd'] = 'sell'
    else:
        signals['macd'] = 'hold'

    # Combine Signals (at least 2 out of 3)
    buy_signals = sum(1 for s in signals.values() if s == 'buy')
    sell_signals = sum(1 for s in signals.values() if s == 'sell')

    if buy_signals >= 2:
        return 'buy', signals
    elif sell_signals >= 2:
        return 'sell', signals
    else:
        return 'hold', signals

# --- Trade Execution ---
def execute_trade(signal, binance, oanda, df):
    """Executes a trade with risk management."""
    print(f"\n--- New Signal ---")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Signal: {signal}")

    if signal not in ['buy', 'sell']:
        print("Action: Hold.")
        return

    if MARKET_TYPE == 'crypto':
        try:
            # Get account balance
            balance = binance.fetch_balance()
            usdt_balance = balance['total']['USDT']
            print(f"Current USDT Balance: {usdt_balance:.2f}")

            # Calculate position size
            last_price = df['close'].iloc[-1]
            risk_amount = usdt_balance * (RISK_PER_TRADE_PERCENT / 100)
            stop_loss_price_diff = last_price * (STOP_LOSS_PERCENT / 100)
            position_size = risk_amount / stop_loss_price_diff
            
            print(f"Risking ${risk_amount:.2f} to open a position of {position_size:.4f} BTC")

            # Define Stop Loss and Take Profit prices
            if signal == 'buy':
                stop_loss_price = last_price * (1 - STOP_LOSS_PERCENT / 100)
                take_profit_price = last_price * (1 + TAKE_PROFIT_PERCENT / 100)
                side = 'buy'
            else: # sell
                stop_loss_price = last_price * (1 + STOP_LOSS_PERCENT / 100)
                take_profit_price = last_price * (1 - TAKE_PROFIT_PERCENT / 100)
                side = 'sell'

            params = {
                'stopLoss': {
                    'type': 'STOP_MARKET',
                    'price': stop_loss_price,
                },
                'takeProfit': {
                    'type': 'TAKE_PROFIT_MARKET',
                    'price': take_profit_price,
                }
            }

            print(f"Action: Placing {side.upper()} order for {position_size:.4f} {TRADING_PAIR_CRYPTO}.")
            print(f"Stop Loss Price: {stop_loss_price:.2f}")
            print(f"Take Profit Price: {take_profit_price:.2f}")

            # Create the order
            order = binance.create_order(TRADING_PAIR_CRYPTO, 'market', side, position_size, params=params)
            print("Order placed successfully:")
            print(order)

        except ccxt.BaseError as e:
            print(f"An error occurred during trade execution: {e}")

    elif MARKET_TYPE == 'forex':
        print("Forex trading with risk management is not yet implemented.")
        pass

# --- Main Loop ---
def main():
    """Main trading loop."""
    binance, oanda = initialize_apis()

    while True:
        try:
            df = fetch_data(binance, oanda)
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                signal, individual_signals = generate_signal(df)
                
                print(f"\n--- Indicator Values ---")
                print(df.iloc[-1])
                print(f"\n--- Individual Signals ---")
                print(individual_signals)

                execute_trade(signal, binance, oanda, df)
            else:
                print("Could not fetch data. Retrying...")

        except Exception as e:
            print(f"An error occurred in the main loop: {e}")

        print("\nWaiting for the next candle...")
        time.sleep(3600)  # Wait for 1 hour

if __name__ == "__main__":
    main()