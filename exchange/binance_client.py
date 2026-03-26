"""
Binance exchange API wrapper using ccxt.
Handles OHLCV fetching, order placement, balance queries, and retry logic.
"""

import time
import logging
import ccxt
import pandas as pd

logger = logging.getLogger("trading_bot")

# [SECURE] Max retry cap - prevents infinite loop (Category 3)
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2
RATE_LIMIT_DELAY = 30


class ExchangeConnectionError(Exception):
    """Raised when exchange connection fails after all retries."""
    pass


class BinanceExchange:
    """Wrapper around ccxt Binance client with retry logic."""

    def __init__(self, api_key: str, api_secret: str, dry_run: bool = True):
        """Initialize Binance exchange client.

        Args:
            api_key: Binance API key.
            api_secret: Binance API secret.
            dry_run: If True, use sandbox/testnet mode.
        """
        # [SECURE] Credentials from parameters, not hard-coded (Category 2)
        self._exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
        self._dry_run = dry_run

        # DRY_RUN: use REAL Binance for market data (read-only), simulate orders
        # Do NOT use sandbox/testnet (API keys are for live Binance)
        if dry_run:
            logger.info("Exchange initialized in DRY RUN mode (real data, simulated orders)")
        else:
            logger.info("Exchange initialized in LIVE mode")

    def _retry(self, func, *args, **kwargs):
        """Execute a function with retry logic for transient errors.

        Args:
            func: Callable to execute.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Result of the function call.

        Raises:
            ExchangeConnectionError: After exhausting all retries.
            ccxt.AuthenticationError: Immediately, no retry.
        """
        last_error = None
        # [SECURE] Bounded retry loop - prevents infinite loop (Category 3)
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except ccxt.AuthenticationError as e:
                # [SECURE] Log generic message to prevent info exposure (Category 4)
                logger.error("Authentication failed. Check API credentials.")
                raise
            except ccxt.RateLimitExceeded as e:
                logger.warning("Rate limit exceeded, waiting %ds...", RATE_LIMIT_DELAY)
                time.sleep(RATE_LIMIT_DELAY)
                last_error = e
            except (ccxt.NetworkError, ccxt.ExchangeNotAvailable, ccxt.RequestTimeout) as e:
                delay = RETRY_BASE_DELAY ** (attempt + 1)
                logger.warning(
                    "Network error (attempt %d/%d), retrying in %ds...",
                    attempt + 1, MAX_RETRIES, delay
                )
                time.sleep(delay)
                last_error = e
            except ccxt.ExchangeError as e:
                # [SECURE] Log full error to file only - no exposure to user (Category 4)
                logger.error("Exchange error: %s", e)
                raise

        raise ExchangeConnectionError(
            f"Failed after {MAX_RETRIES} retries: {last_error}"
        )

    def test_connectivity(self) -> bool:
        """Test connection to Binance.

        Returns:
            True if connection is successful.
        """
        try:
            self._retry(self._exchange.fetch_time)
            logger.info("Exchange connectivity test passed")
            return True
        except Exception as e:
            logger.error("Exchange connectivity test failed: %s", type(e).__name__)
            return False

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV candlestick data.

        Args:
            symbol: Trading pair (e.g., 'ETH/USDT').
            timeframe: Candle timeframe (e.g., '1h', '4h', '1d').
            limit: Number of candles to fetch.

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume.
        """
        # [SECURE] Null check before use - prevents null pointer dereference (Category 5)
        if not symbol:
            raise ValueError("Symbol must not be empty")

        raw = self._retry(self._exchange.fetch_ohlcv, symbol, timeframe, limit=limit)

        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    def fetch_ticker_price(self, symbol: str) -> float:
        """Fetch current market price.

        Args:
            symbol: Trading pair.

        Returns:
            Current last price as float.
        """
        ticker = self._retry(self._exchange.fetch_ticker, symbol)
        # [SECURE] Null check - prevents null pointer dereference (Category 5)
        if ticker is None or "last" not in ticker:
            raise ExchangeConnectionError("Failed to fetch ticker data")
        return float(ticker["last"])

    def fetch_balance(self, asset: str) -> dict:
        """Fetch balance for a specific asset.

        Args:
            asset: Asset symbol (e.g., 'ETH', 'USDT').

        Returns:
            Dict with 'free' and 'total' balances.
        """
        if self._dry_run:
            # [SECURE] DRY_RUN returns simulated balance (no API call needed)
            sim_balances = {"USDT": 333.33, "ETH": 0.0}
            bal = sim_balances.get(asset, 0.0)
            logger.debug("[DRY RUN] Simulated balance for %s: %.2f", asset, bal)
            return {"free": bal, "total": bal}

        balance = self._retry(self._exchange.fetch_balance)
        # [SECURE] Null check before access (Category 5)
        if balance is None or asset not in balance:
            return {"free": 0.0, "total": 0.0}

        return {
            "free": float(balance[asset].get("free", 0.0)),
            "total": float(balance[asset].get("total", 0.0)),
        }

    def create_market_buy(self, symbol: str, amount: float) -> dict:
        """Place a market buy order.

        Args:
            symbol: Trading pair.
            amount: Quantity to buy in base asset.

        Returns:
            Order result dict.
        """
        if self._dry_run:
            logger.info("[DRY RUN] Market BUY: %s %.6f", symbol, amount)
            return {"id": "dry_run", "status": "simulated", "side": "buy", "amount": amount}

        logger.info("Placing market BUY: %s %.6f", symbol, amount)
        result = self._retry(self._exchange.create_market_buy_order, symbol, amount)
        logger.info("BUY order filled: ID=%s, Amount=%.6f", result.get("id"), result.get("filled", 0))
        return result

    def create_market_sell(self, symbol: str, amount: float) -> dict:
        """Place a market sell order.

        Args:
            symbol: Trading pair.
            amount: Quantity to sell in base asset.

        Returns:
            Order result dict.
        """
        if self._dry_run:
            logger.info("[DRY RUN] Market SELL: %s %.6f", symbol, amount)
            return {"id": "dry_run", "status": "simulated", "side": "sell", "amount": amount}

        logger.info("Placing market SELL: %s %.6f", symbol, amount)
        result = self._retry(self._exchange.create_market_sell_order, symbol, amount)
        logger.info("SELL order filled: ID=%s, Amount=%.6f", result.get("id"), result.get("filled", 0))
        return result

    def create_stop_loss_order(self, symbol: str, amount: float, stop_price: float) -> dict:
        """Place a stop-loss limit order.

        Args:
            symbol: Trading pair.
            amount: Quantity.
            stop_price: Trigger price for the stop loss.

        Returns:
            Order result dict.
        """
        if self._dry_run:
            logger.info("[DRY RUN] STOP LOSS: %s %.6f @ %.2f", symbol, amount, stop_price)
            return {"id": "dry_run", "status": "simulated", "type": "stop_loss", "stopPrice": stop_price}

        logger.info("Placing STOP LOSS: %s %.6f @ %.2f", symbol, amount, stop_price)
        params = {"stopPrice": stop_price}
        result = self._retry(
            self._exchange.create_order,
            symbol, "stop_loss_limit", "sell", amount, stop_price, params
        )
        logger.info("STOP LOSS order placed: ID=%s", result.get("id"))
        return result

    def cancel_all_orders(self, symbol: str) -> None:
        """Cancel all open orders for a symbol.

        Args:
            symbol: Trading pair.
        """
        if self._dry_run:
            logger.info("[DRY RUN] Cancel all orders for %s", symbol)
            return

        try:
            open_orders = self._retry(self._exchange.fetch_open_orders, symbol)
            for order in open_orders:
                self._retry(self._exchange.cancel_order, order["id"], symbol)
                logger.info("Cancelled order: %s", order["id"])
        except ccxt.ExchangeError as e:
            logger.warning("Error cancelling orders: %s", e)

    def get_symbol_info(self, symbol: str) -> dict:
        """Get trading pair info (min quantity, step size, etc.).

        Args:
            symbol: Trading pair.

        Returns:
            Market info dict.
        """
        markets = self._retry(self._exchange.load_markets)
        # [SECURE] Null check (Category 5)
        if symbol not in markets:
            raise ValueError(f"Symbol {symbol} not found on exchange")
        return markets[symbol]


# --------------------------------------------------
# Security Checklist
# Applied:
#   - Hard-coded credentials prevention: keys passed as parameters (Category 2)
#   - Error message info exposure prevention: generic messages to console (Category 4)
#   - Proper exception handling: no empty except blocks (Category 4)
#   - Null pointer dereference prevention: null checks on API responses (Category 5)
#   - Infinite loop prevention: bounded retry with MAX_RETRIES (Category 3)
#   - Resource release: ccxt handles connection pooling internally
# Not Applied:
#   - [WARN] SQL Injection: not applicable - no database used
#   - [WARN] XSS: not applicable - no HTML output
# --------------------------------------------------
