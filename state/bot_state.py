"""
Thread-safe shared state between trading bot and web dashboard.
"""

import threading
import time
import logging
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("trading_bot")


class BotState:
    """Thread-safe singleton holding all bot state for the dashboard."""

    def __init__(self):
        self._lock = threading.Lock()

        # Trading status
        self.auto_trading_enabled: bool = True
        self.is_running: bool = False
        self.dry_run: bool = True
        self.cycle_count: int = 0
        self.last_update_time: float = 0.0

        # Price & indicators
        self.current_price: float = 0.0
        self.rsi: float | None = None
        self.bb_upper: float | None = None
        self.bb_lower: float | None = None
        self.macd_hist_up: bool = False
        self.macd_hist_down: bool = False
        self.volume_ratio: float | None = None
        self.price_momentum: float | None = None
        self.ema20: float | None = None

        # Trend & mode
        self.trend_strength: float = 0.0
        self.trend_direction: str = "NONE"
        self.trading_mode: str = "RANGE"

        # Sentiment & smart money
        self.fear_greed: int | None = None
        self.smart_money_score: float = 0.0
        self.smart_money_signal: str = "NEUTRAL"
        self.sm_components: dict = {}

        # Position
        self.has_position: bool = False
        self.position_entries: int = 0
        self.position_avg_price: float = 0.0
        self.position_quantity: float = 0.0
        self.position_invested: float = 0.0
        self.position_pnl_pct: float = 0.0
        self.position_pnl_usdt: float = 0.0
        self.position_sl: float = 0.0
        self.position_tp: float = 0.0
        self.position_holding_bars: int = 0

        # Last signal
        self.last_signal: str = "HOLD"

        # Price history for chart (last 50 prices)
        self.price_history: list = []
        self._max_history: int = 50

        # Mutable settings (UI can change these)
        self.settings: dict = {}

    @staticmethod
    def _to_native(value):
        """Convert numpy types to Python native for JSON serialization."""
        if hasattr(value, 'item'):  # numpy scalar
            return value.item()
        return value

    def update_indicators(self, **kwargs) -> None:
        """Update indicator values from trading loop."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, self._to_native(value))
            self.last_update_time = time.time()
            self.cycle_count += 1

            # Track price history for chart
            if "current_price" in kwargs and kwargs["current_price"] > 0:
                self.price_history.append({
                    "time": time.time(),
                    "price": self._to_native(kwargs["current_price"])
                })
                # [SECURE] Bounded list (Category 3)
                if len(self.price_history) > self._max_history:
                    self.price_history = self.price_history[-self._max_history:]

    def update_position(self, has_position: bool, **kwargs) -> None:
        """Update position state."""
        with self._lock:
            self.has_position = has_position
            if has_position:
                for key, value in kwargs.items():
                    attr = f"position_{key}"
                    if hasattr(self, attr):
                        setattr(self, attr, value)
            else:
                self.position_entries = 0
                self.position_avg_price = 0.0
                self.position_quantity = 0.0
                self.position_invested = 0.0
                self.position_pnl_pct = 0.0
                self.position_pnl_usdt = 0.0
                self.position_sl = 0.0
                self.position_tp = 0.0
                self.position_holding_bars = 0

    def get_snapshot(self) -> dict:
        """Get a thread-safe copy of all state for the UI."""
        with self._lock:
            return {
                "auto_trading": self.auto_trading_enabled,
                "is_running": self.is_running,
                "dry_run": self.dry_run,
                "cycle": self.cycle_count,
                "last_update": self.last_update_time,
                "price": self.current_price,
                "rsi": self.rsi,
                "bb_upper": self.bb_upper,
                "bb_lower": self.bb_lower,
                "macd_up": self.macd_hist_up,
                "macd_down": self.macd_hist_down,
                "volume_ratio": self.volume_ratio,
                "momentum": self.price_momentum,
                "trend_strength": self.trend_strength,
                "trend_direction": self.trend_direction,
                "mode": self.trading_mode,
                "fear_greed": self.fear_greed,
                "sm_score": self.smart_money_score,
                "sm_signal": self.smart_money_signal,
                "sm_components": dict(self.sm_components),
                "has_position": self.has_position,
                "pos_entries": self.position_entries,
                "pos_avg": self.position_avg_price,
                "pos_qty": self.position_quantity,
                "pos_invested": self.position_invested,
                "pos_pnl_pct": self.position_pnl_pct,
                "pos_pnl_usdt": self.position_pnl_usdt,
                "pos_sl": self.position_sl,
                "pos_tp": self.position_tp,
                "pos_hold_bars": self.position_holding_bars,
                "signal": self.last_signal,
                "price_history": list(self.price_history),
                "settings": dict(self.settings),
            }

    def update_setting(self, key: str, value) -> bool:
        """Update a single setting value. Returns True if accepted."""
        with self._lock:
            if key in self.settings:
                self.settings[key] = value
                logger.info("Setting updated via UI: %s = %s", key, value)
                return True
            return False

    def reset_settings(self, defaults: dict) -> None:
        """Reset all settings to provided defaults."""
        with self._lock:
            self.settings.update(defaults)
            logger.info("Settings reset to optimized defaults")


# --------------------------------------------------
# Security Checklist
# Applied:
#   - Race condition prevention: threading.Lock on all mutations (Category 3)
#   - Bounded collection: price_history capped at max_history (Category 3)
#   - Proper logging: setting changes logged (Category 4)
# Not Applied:
#   - [WARN] SQL Injection: not applicable here (handled in trade_db.py)
# --------------------------------------------------
