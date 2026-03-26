"""
Optimized default values derived from 475-trade backtest analysis.
Used by the "Reset to Optimized Defaults" button in the dashboard.
"""

OPTIMIZED_DEFAULTS = {
    # Technical indicator thresholds
    "rsi_buy_threshold": 35.0,
    "rsi_sell_threshold": 72.0,
    "bb_buy_multiplier": 1.02,
    "bb_sell_multiplier": 0.98,
    "fg_buy_threshold": 35.0,
    "fg_sell_threshold": 75.0,
    # Risk management
    "max_position_percent": 0.15,
    "stop_loss_percent": 0.08,
    "take_profit_percent": 0.10,
    "min_order_size_usdt": 10.0,
    # DCA
    "dca_enabled": True,
    "dca_max_entries": 4,
    "dca_drop_percent_1": 0.04,
    "dca_drop_percent_2": 0.08,
    "dca_drop_percent_3": 0.12,
    "dca_multiplier_1": 1.5,
    "dca_multiplier_2": 2.0,
    "dca_multiplier_3": 2.5,
    "dca_max_total_percent": 0.40,
    "dca_require_signal": True,
    # Dual-Mode
    "trend_threshold": 50.0,
    "trend_position_multiplier": 4.0,
    "trend_trailing_stop_pct": 0.04,
    "trend_min_hold_bars": 6,
    "range_min_hold_bars": 3,
    # Loop
    "trading_interval_seconds": 300,
}
