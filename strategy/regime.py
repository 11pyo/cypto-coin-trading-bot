"""
Market Regime Detector - Adaptive Strategy Engine

Detects current market regime using multiple signals and adjusts
strategy parameters in real-time.

Regimes:
  BULL:     Strong uptrend confirmed by EMA + volume + sentiment
  BEAR:     Strong downtrend confirmed by EMA + volume + sentiment
  SIDEWAYS: No clear direction, range-bound market
  VOLATILE: High volatility regardless of direction

Each regime has its own parameter profile:
  BULL -> Aggressive: bigger positions, trailing stop, hold longer
  BEAR -> Defensive:  smaller positions, tight stops, quick exits
  SIDEWAYS -> Neutral: standard mean-reversion strategy
  VOLATILE -> Cautious: reduced size, wider stops, strict filters
"""

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("trading_bot")


class MarketRegime(Enum):
    """Market regime classification."""
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"
    VOLATILE = "VOLATILE"


@dataclass
class RegimeParams:
    """Strategy parameters adapted for a specific market regime."""
    # Position sizing
    position_size_mult: float    # multiplier on base position %
    # Stop loss / Take profit
    sl_mult: float               # multiplier on base SL %
    tp_mult: float               # multiplier on base TP %
    use_trailing_stop: bool      # enable trailing stop instead of fixed TP
    trailing_stop_pct: float     # trailing stop distance (% from peak)
    # Signal filtering
    min_hold_bars: int           # minimum bars before signal-sell allowed
    cooldown_bars: int           # cooldown between trades
    volume_filter: float         # minimum volume ratio to accept signals
    # DCA behavior
    dca_aggressiveness: float    # multiplier on DCA order sizes
    # Description
    description: str


# Pre-defined regime profiles
REGIME_PROFILES = {
    MarketRegime.BULL: RegimeParams(
        position_size_mult=2.0,      # 2x bigger positions in bull
        sl_mult=1.5,                 # wider SL (let it breathe)
        tp_mult=2.5,                 # much higher TP target
        use_trailing_stop=True,      # ride the trend with trailing stop
        trailing_stop_pct=0.05,      # 5% trailing from peak
        min_hold_bars=6,             # hold at least 6 hours
        cooldown_bars=4,             # moderate cooldown
        volume_filter=0.4,           # accept more signals (trend is friend)
        dca_aggressiveness=1.5,      # aggressive DCA on dips
        description="Aggressive: ride the trend, trailing stop, bigger size"
    ),
    MarketRegime.BEAR: RegimeParams(
        position_size_mult=0.5,      # half-size positions
        sl_mult=0.75,                # tighter SL (cut losses fast)
        tp_mult=0.8,                 # lower TP (take profits quickly)
        use_trailing_stop=False,     # fixed TP, don't get greedy
        trailing_stop_pct=0.0,
        min_hold_bars=2,             # short holds
        cooldown_bars=8,             # long cooldown (trade less)
        volume_filter=0.7,           # strict volume filter
        dca_aggressiveness=0.5,      # conservative DCA
        description="Defensive: small positions, tight stops, trade less"
    ),
    MarketRegime.SIDEWAYS: RegimeParams(
        position_size_mult=1.0,      # standard size
        sl_mult=1.0,                 # standard SL
        tp_mult=1.0,                 # standard TP
        use_trailing_stop=False,
        trailing_stop_pct=0.0,
        min_hold_bars=3,
        cooldown_bars=6,
        volume_filter=0.6,
        dca_aggressiveness=1.0,
        description="Neutral: standard mean-reversion parameters"
    ),
    MarketRegime.VOLATILE: RegimeParams(
        position_size_mult=0.7,      # reduced size
        sl_mult=1.8,                 # much wider SL (avoid whipsaws)
        tp_mult=1.5,                 # higher TP (volatility = bigger moves)
        use_trailing_stop=True,      # trailing stop captures swings
        trailing_stop_pct=0.07,      # wider trailing (7%)
        min_hold_bars=4,
        cooldown_bars=8,             # long cooldown
        volume_filter=0.5,
        dca_aggressiveness=0.8,
        description="Cautious: wider stops, reduced size, ride swings"
    ),
}


class RegimeDetector:
    """Detects market regime using multiple signals.

    Uses a scoring system combining:
      - EMA trend (20/50): direction
      - Volume trend: participation confirmation
      - Fear/Greed: crowd sentiment
      - ATR ratio: volatility level
      - Price momentum: speed of move
    """

    def __init__(self):
        # [SECURE] Initialized variable (Category 5)
        self._current_regime: MarketRegime = MarketRegime.SIDEWAYS
        self._regime_confidence: float = 0.0
        self._regime_history: list = []
        self._max_history: int = 10  # [SECURE] Max cap - prevents unbounded growth (Category 3)

    @property
    def current_regime(self) -> MarketRegime:
        """Get the current detected regime."""
        return self._current_regime

    @property
    def confidence(self) -> float:
        """Get confidence level of current regime detection (0-100)."""
        return self._regime_confidence

    @property
    def params(self) -> RegimeParams:
        """Get the parameter profile for the current regime."""
        return REGIME_PROFILES[self._current_regime]

    def detect(
        self,
        trend: str,
        volume_ratio: float | None,
        fear_greed: int | None,
        atr_ratio: float | None,
        price_momentum: float | None,
        rsi: float | None,
    ) -> MarketRegime:
        """Detect market regime from current indicators.

        Args:
            trend: 'UPTREND', 'DOWNTREND', or 'NEUTRAL' from EMA crossover.
            volume_ratio: Current volume / 20-period average.
            fear_greed: Fear/Greed index (0-100).
            atr_ratio: Current ATR / price (normalized volatility).
            price_momentum: 5-bar price change rate.
            rsi: Current RSI value.

        Returns:
            Detected MarketRegime.
        """
        # Scoring system: each signal contributes to regime scores
        bull_score = 0.0
        bear_score = 0.0
        volatile_score = 0.0
        total_weight = 0.0

        # --- Signal 1: EMA Trend (weight: 30%) ---
        weight = 30.0
        total_weight += weight
        if trend == "UPTREND":
            bull_score += weight
        elif trend == "DOWNTREND":
            bear_score += weight
        # NEUTRAL contributes to neither

        # --- Signal 2: Volume (weight: 15%) ---
        if volume_ratio is not None:
            weight = 15.0
            total_weight += weight
            if volume_ratio > 1.5:
                # High volume confirms the current trend
                if trend == "UPTREND":
                    bull_score += weight
                elif trend == "DOWNTREND":
                    bear_score += weight
                else:
                    volatile_score += weight  # high volume without trend = volatile
            elif volume_ratio > 1.0:
                # Moderate volume - slight confirmation
                if trend == "UPTREND":
                    bull_score += weight * 0.5
                elif trend == "DOWNTREND":
                    bear_score += weight * 0.5

        # --- Signal 3: Fear/Greed (weight: 25%) ---
        if fear_greed is not None:
            weight = 25.0
            total_weight += weight
            if fear_greed >= 60:
                bull_score += weight * (fear_greed / 100)
            elif fear_greed <= 30:
                bear_score += weight * ((100 - fear_greed) / 100)
            elif fear_greed <= 15:
                # Extreme fear - likely capitulation, could be bottom
                bear_score += weight * 0.5
                bull_score += weight * 0.3  # contrarian signal

        # --- Signal 4: ATR (volatility) (weight: 15%) ---
        if atr_ratio is not None:
            weight = 15.0
            total_weight += weight
            if atr_ratio > 0.04:       # >4% daily range = very volatile
                volatile_score += weight
            elif atr_ratio > 0.025:     # >2.5% = moderately volatile
                volatile_score += weight * 0.5

        # --- Signal 5: Price Momentum (weight: 15%) ---
        if price_momentum is not None:
            weight = 15.0
            total_weight += weight
            if price_momentum > 0.05:   # >5% in 5 bars
                bull_score += weight
            elif price_momentum > 0.02:
                bull_score += weight * 0.5
            elif price_momentum < -0.05:
                bear_score += weight
            elif price_momentum < -0.02:
                bear_score += weight * 0.5

        # --- Determine regime ---
        # [SECURE] Division by zero prevention (Category 5)
        if total_weight <= 0:
            return self._current_regime

        # Normalize scores
        bull_pct = (bull_score / total_weight) * 100
        bear_pct = (bear_score / total_weight) * 100
        volatile_pct = (volatile_score / total_weight) * 100

        # Volatility override: if volatility is extreme, regime = VOLATILE
        if volatile_pct > 40:
            new_regime = MarketRegime.VOLATILE
            confidence = volatile_pct
        elif bull_pct > 50:
            new_regime = MarketRegime.BULL
            confidence = bull_pct
        elif bear_pct > 50:
            new_regime = MarketRegime.BEAR
            confidence = bear_pct
        elif bull_pct > 30 and bull_pct > bear_pct:
            new_regime = MarketRegime.BULL
            confidence = bull_pct
        elif bear_pct > 30 and bear_pct > bull_pct:
            new_regime = MarketRegime.BEAR
            confidence = bear_pct
        else:
            new_regime = MarketRegime.SIDEWAYS
            confidence = 100 - max(bull_pct, bear_pct, volatile_pct)

        # Regime change smoothing: require 2 consecutive same detections
        self._regime_history.append(new_regime)
        # [SECURE] Bounded list size (Category 3)
        if len(self._regime_history) > self._max_history:
            self._regime_history = self._regime_history[-self._max_history:]

        if len(self._regime_history) >= 2 and self._regime_history[-1] == self._regime_history[-2]:
            if new_regime != self._current_regime:
                logger.info(
                    "REGIME CHANGE: %s -> %s (confidence: %.0f%%) "
                    "[Bull:%.0f%% Bear:%.0f%% Volatile:%.0f%%]",
                    self._current_regime.value, new_regime.value, confidence,
                    bull_pct, bear_pct, volatile_pct
                )
                self._current_regime = new_regime
                self._regime_confidence = confidence
        else:
            # Keep current regime if not confirmed
            pass

        self._regime_confidence = confidence

        logger.debug(
            "Regime: %s (%.0f%%) | Scores: Bull=%.0f%% Bear=%.0f%% Vol=%.0f%% | "
            "Inputs: trend=%s vol=%.2f fg=%s atr=%s mom=%s",
            self._current_regime.value, confidence,
            bull_pct, bear_pct, volatile_pct,
            trend,
            volume_ratio if volume_ratio is not None else 0,
            str(fear_greed) if fear_greed is not None else "N/A",
            f"{atr_ratio:.4f}" if atr_ratio is not None else "N/A",
            f"{price_momentum:.3f}" if price_momentum is not None else "N/A"
        )

        return self._current_regime

    def get_summary(self) -> str:
        """Get a formatted summary for dashboard logging."""
        params = self.params
        return (
            f"Regime={self._current_regime.value}({self._regime_confidence:.0f}%) "
            f"[Size:x{params.position_size_mult:.1f} "
            f"SL:x{params.sl_mult:.1f} "
            f"TP:x{params.tp_mult:.1f} "
            f"{'Trail' if params.use_trailing_stop else 'Fixed'}]"
        )


# --------------------------------------------------
# Security Checklist
# Applied:
#   - Null pointer dereference prevention: null checks on all inputs (Category 5)
#   - Division by zero prevention: total_weight check (Category 5)
#   - Initialized variables: all state initialized at declaration (Category 5)
#   - Bounded collection: regime_history capped at max_history (Category 3)
#   - Proper logging: meaningful messages on regime changes (Category 4)
# Not Applied:
#   - [WARN] SQL Injection: not applicable - no database used
#   - [WARN] Race Condition: single-threaded, no concurrent access
# --------------------------------------------------
