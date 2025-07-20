# Python Trading Bot for Forex and Crypto

This is a Python-based automated trading bot that supports both forex (OANDA) and crypto (Binance) markets. It uses a combination of technical indicators to generate trading signals.

## Features

- **Markets**: Binance (Crypto) and OANDA (Forex)
- **Trading Mode**: Paper/Testnet trading
- **Strategy**: EMA Crossover, RSI, and MACD (2 out of 3 confirmation)
- **Timeframe**: 1-hour (1h)
- **Modular Code**: Easy to extend and customize

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install the required libraries:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Create a `.env` file** by copying the `.env.example` file:
    ```bash
    cp .env.example .env
    ```

4.  **Add your API keys** to the `.env` file. 
    - For Binance, you'll need an API key and secret key for the **Futures Testnet**.
    - For OANDA, you'll need an API key and account ID for a **demo account**.

## How to Run

1.  **Configure the bot** in `trading_bot.py`:
    - Set `MARKET_TYPE` to `'crypto'` or `'forex'`.
    - Adjust other parameters like `TRADING_PAIR_CRYPTO`, `TRADING_PAIR_FOREX`, etc., as needed.

2.  **Run the bot:**
    ```bash
    python trading_bot.py
    ```

The bot will run in a loop, fetching data and generating signals every hour.

## Disclaimer

This trading bot is for educational purposes only. Trading financial markets involves significant risk. Use this bot at your own risk. The author is not responsible for any financial losses.
