"""
Configuration module - loads and validates all settings from environment variables.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Settings:
    """Trading bot configuration loaded from environment variables."""

    # Binance API
    binance_api_key: str
    binance_api_secret: str

    # Trading pair
    trading_symbol: str
    base_asset: str
    quote_asset: str

    # RSI parameters
    rsi_period: int
    rsi_buy_threshold: float
    rsi_sell_threshold: float

    # Bollinger Bands parameters
    bb_period: int
    bb_std_dev: float
    bb_buy_multiplier: float
    bb_sell_multiplier: float

    # MACD parameters
    macd_fast: int
    macd_slow: int
    macd_signal: int

    # Fear & Greed parameters
    fg_buy_threshold: float
    fg_sell_threshold: float

    # Risk management
    max_position_percent: float
    stop_loss_percent: float
    take_profit_percent: float
    max_open_positions: int
    min_order_size_usdt: float

    # DCA (Dollar Cost Averaging) parameters
    dca_enabled: bool
    dca_max_entries: int
    dca_drop_percent_1: float
    dca_drop_percent_2: float
    dca_drop_percent_3: float
    dca_multiplier_1: float
    dca_multiplier_2: float
    dca_multiplier_3: float
    dca_max_total_percent: float
    dca_require_signal: bool

    # Dual-Mode parameters
    trend_threshold: float
    trend_position_multiplier: float
    trend_trailing_stop_pct: float
    trend_min_hold_bars: int
    range_min_hold_bars: int

    # Loop control
    trading_interval_seconds: int
    ohlcv_timeframe: str
    ohlcv_limit: int

    # Mode
    dry_run: bool

    # Logging
    log_level: str
    log_file: str


def load_settings() -> Settings:
    """Load settings from .env file and environment variables.

    Returns:
        Settings dataclass with all configuration values.

    Raises:
        EnvironmentError: If required environment variables are missing.
    """
    # [SECURE] Load from .env file - prevents hard-coded credentials (Category 2)
    load_dotenv()

    # [SECURE] Validate required secrets exist - prevents missing credential errors
    api_key = os.environ.get("BINANCE_API_KEY", "")
    api_secret = os.environ.get("BINANCE_API_SECRET", "")

    if not api_key or api_key == "your_api_key_here":
        raise EnvironmentError(
            "BINANCE_API_KEY environment variable is not set or contains placeholder value."
        )
    if not api_secret or api_secret == "your_api_secret_here":
        raise EnvironmentError(
            "BINANCE_API_SECRET environment variable is not set or contains placeholder value."
        )

    return Settings(
        # [SECURE] Credentials from environment only - no hard-coded values (Category 2)
        binance_api_key=api_key,
        binance_api_secret=api_secret,
        trading_symbol=os.environ.get("TRADING_SYMBOL", "ETHUSDT"),
        base_asset=os.environ.get("BASE_ASSET", "ETH"),
        quote_asset=os.environ.get("QUOTE_ASSET", "USDT"),
        rsi_period=int(os.environ.get("RSI_PERIOD", "14")),
        rsi_buy_threshold=float(os.environ.get("RSI_BUY_THRESHOLD", "35.0")),
        rsi_sell_threshold=float(os.environ.get("RSI_SELL_THRESHOLD", "70.0")),
        bb_period=int(os.environ.get("BB_PERIOD", "20")),
        bb_std_dev=float(os.environ.get("BB_STD_DEV", "2.0")),
        bb_buy_multiplier=float(os.environ.get("BB_BUY_MULTIPLIER", "1.02")),
        bb_sell_multiplier=float(os.environ.get("BB_SELL_MULTIPLIER", "0.98")),
        macd_fast=int(os.environ.get("MACD_FAST", "12")),
        macd_slow=int(os.environ.get("MACD_SLOW", "26")),
        macd_signal=int(os.environ.get("MACD_SIGNAL", "9")),
        fg_buy_threshold=float(os.environ.get("FG_BUY_THRESHOLD", "35.0")),
        fg_sell_threshold=float(os.environ.get("FG_SELL_THRESHOLD", "75.0")),
        max_position_percent=float(os.environ.get("MAX_POSITION_PERCENT", "0.10")),
        stop_loss_percent=float(os.environ.get("STOP_LOSS_PERCENT", "0.05")),
        take_profit_percent=float(os.environ.get("TAKE_PROFIT_PERCENT", "0.10")),
        max_open_positions=int(os.environ.get("MAX_OPEN_POSITIONS", "1")),
        min_order_size_usdt=float(os.environ.get("MIN_ORDER_SIZE_USDT", "10.0")),
        # DCA settings
        dca_enabled=os.environ.get("DCA_ENABLED", "true").lower() == "true",
        dca_max_entries=int(os.environ.get("DCA_MAX_ENTRIES", "4")),
        dca_drop_percent_1=float(os.environ.get("DCA_DROP_PERCENT_1", "0.05")),
        dca_drop_percent_2=float(os.environ.get("DCA_DROP_PERCENT_2", "0.10")),
        dca_drop_percent_3=float(os.environ.get("DCA_DROP_PERCENT_3", "0.15")),
        dca_multiplier_1=float(os.environ.get("DCA_MULTIPLIER_1", "1.5")),
        dca_multiplier_2=float(os.environ.get("DCA_MULTIPLIER_2", "2.0")),
        dca_multiplier_3=float(os.environ.get("DCA_MULTIPLIER_3", "2.5")),
        dca_max_total_percent=float(os.environ.get("DCA_MAX_TOTAL_PERCENT", "0.40")),
        dca_require_signal=os.environ.get("DCA_REQUIRE_SIGNAL", "true").lower() == "true",
        # Dual-Mode settings
        trend_threshold=float(os.environ.get("TREND_THRESHOLD", "50.0")),
        trend_position_multiplier=float(os.environ.get("TREND_POSITION_MULTIPLIER", "4.0")),
        trend_trailing_stop_pct=float(os.environ.get("TREND_TRAILING_STOP_PCT", "0.04")),
        trend_min_hold_bars=int(os.environ.get("TREND_MIN_HOLD_BARS", "6")),
        range_min_hold_bars=int(os.environ.get("RANGE_MIN_HOLD_BARS", "3")),
        trading_interval_seconds=int(os.environ.get("TRADING_INTERVAL_SECONDS", "300")),
        ohlcv_timeframe=os.environ.get("OHLCV_TIMEFRAME", "1h"),
        ohlcv_limit=int(os.environ.get("OHLCV_LIMIT", "100")),
        dry_run=os.environ.get("DRY_RUN", "true").lower() == "true",
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        log_file=os.environ.get("LOG_FILE", "trading_bot.log"),
    )


# --------------------------------------------------
# Security Checklist
# Applied:
#   - Hard-coded credentials prevention: API keys loaded from env vars only (Category 2)
#   - Placeholder detection: rejects default .env.example values
#   - Missing credential validation: raises EnvironmentError if keys are absent
# Not Applied:
#   - [WARN] SQL Injection: not applicable - no database used
#   - [WARN] XSS: not applicable - no HTML output
# --------------------------------------------------
