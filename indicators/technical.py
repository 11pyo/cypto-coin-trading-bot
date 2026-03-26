"""
Technical indicator calculations: RSI, MACD, Bollinger Bands.
Uses pandas-ta for reliable indicator computation.
"""

import logging
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger("trading_bot")


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index.

    Args:
        df: OHLCV DataFrame with 'close' column.
        period: RSI lookback period.

    Returns:
        RSI series.
    """
    # [SECURE] Null check before use - prevents null pointer dereference (Category 5)
    if df is None or df.empty or "close" not in df.columns:
        raise ValueError("Valid DataFrame with 'close' column is required")

    rsi = ta.rsi(df["close"], length=period)
    return rsi


def calculate_macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> dict:
    """Calculate MACD, signal line, and histogram.

    Args:
        df: OHLCV DataFrame with 'close' column.
        fast: Fast EMA period.
        slow: Slow EMA period.
        signal: Signal line period.

    Returns:
        Dict with keys 'macd', 'signal', 'histogram' (each a pd.Series).
    """
    # [SECURE] Null check (Category 5)
    if df is None or df.empty or "close" not in df.columns:
        raise ValueError("Valid DataFrame with 'close' column is required")

    macd_result = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)

    # [SECURE] Dynamic column detection - column names vary by pandas-ta version (Category 5)
    macd_col = [c for c in macd_result.columns if c.startswith("MACD_") or c.startswith("MACD") and "h" not in c.lower() and "s" not in c.lower()][0]
    hist_col = [c for c in macd_result.columns if c.startswith("MACDh")][0]
    signal_col = [c for c in macd_result.columns if c.startswith("MACDs")][0]

    return {
        "macd": macd_result[macd_col],
        "signal": macd_result[signal_col],
        "histogram": macd_result[hist_col],
    }


def calculate_bollinger_bands(
    df: pd.DataFrame, period: int = 20, std_dev: float = 2.0
) -> dict:
    """Calculate Bollinger Bands.

    Args:
        df: OHLCV DataFrame with 'close' column.
        period: Moving average period.
        std_dev: Number of standard deviations.

    Returns:
        Dict with keys 'upper', 'middle', 'lower' (each a pd.Series).
    """
    # [SECURE] Null check (Category 5)
    if df is None or df.empty or "close" not in df.columns:
        raise ValueError("Valid DataFrame with 'close' column is required")

    bb_result = ta.bbands(df["close"], length=period, std=std_dev)

    # [SECURE] Dynamic column detection - pandas-ta column names vary by version (Category 5)
    upper_col = [c for c in bb_result.columns if c.startswith("BBU")][0]
    middle_col = [c for c in bb_result.columns if c.startswith("BBM")][0]
    lower_col = [c for c in bb_result.columns if c.startswith("BBL")][0]

    return {
        "upper": bb_result[upper_col],
        "middle": bb_result[middle_col],
        "lower": bb_result[lower_col],
    }


def is_macd_histogram_turning_up(histogram: pd.Series) -> bool:
    """Check if MACD histogram is turning upward (momentum shift).

    Args:
        histogram: MACD histogram series.

    Returns:
        True if the latest histogram value is greater than the previous.
    """
    # [SECURE] Null check and length validation (Category 5)
    if histogram is None or len(histogram) < 2:
        return False

    last = histogram.iloc[-1]
    prev = histogram.iloc[-2]

    if pd.isna(last) or pd.isna(prev):
        return False

    return last > prev


def is_macd_histogram_turning_down(histogram: pd.Series) -> bool:
    """Check if MACD histogram is turning downward (momentum shift).

    Args:
        histogram: MACD histogram series.

    Returns:
        True if the latest histogram value is less than the previous.
    """
    # [SECURE] Null check and length validation (Category 5)
    if histogram is None or len(histogram) < 2:
        return False

    last = histogram.iloc[-1]
    prev = histogram.iloc[-2]

    if pd.isna(last) or pd.isna(prev):
        return False

    return last < prev


def calculate_atr(df: pd.DataFrame, period: int = 14) -> float | None:
    """Calculate Average True Range for dynamic SL/TP sizing.

    ATR measures market volatility. Higher ATR = wider SL/TP needed.

    Args:
        df: OHLCV DataFrame with high, low, close columns.
        period: ATR lookback period.

    Returns:
        Latest ATR value as float, or None if calculation fails.
    """
    # [SECURE] Null check (Category 5)
    if df is None or df.empty:
        return None
    for col in ["high", "low", "close"]:
        if col not in df.columns:
            return None

    if len(df) < period + 1:
        return None

    atr_series = ta.atr(df["high"], df["low"], df["close"], length=period)
    if atr_series is None or atr_series.empty:
        return None

    val = atr_series.iloc[-1]
    if pd.isna(val):
        return None
    return float(val)


def calculate_trend_ema(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> str:
    """Detect market trend using EMA crossover.

    Used to adjust position sizing and signal filtering:
    - UPTREND: fast EMA > slow EMA (increase allocation)
    - DOWNTREND: fast EMA < slow EMA (decrease allocation)
    - NEUTRAL: EMAs are close (standard allocation)

    Args:
        df: OHLCV DataFrame with 'close' column.
        fast: Fast EMA period.
        slow: Slow EMA period.

    Returns:
        'UPTREND', 'DOWNTREND', or 'NEUTRAL'.
    """
    # [SECURE] Null check (Category 5)
    if df is None or df.empty or "close" not in df.columns:
        return "NEUTRAL"

    if len(df) < slow + 5:
        return "NEUTRAL"

    ema_fast = ta.ema(df["close"], length=fast)
    ema_slow = ta.ema(df["close"], length=slow)

    if ema_fast is None or ema_slow is None:
        return "NEUTRAL"

    fast_val = ema_fast.iloc[-1]
    slow_val = ema_slow.iloc[-1]

    if pd.isna(fast_val) or pd.isna(slow_val) or slow_val <= 0:
        return "NEUTRAL"

    # Require >1% separation to confirm trend
    spread = (fast_val - slow_val) / slow_val
    if spread > 0.01:
        return "UPTREND"
    elif spread < -0.01:
        return "DOWNTREND"
    return "NEUTRAL"


def calculate_volume_ratio(df: pd.DataFrame, period: int = 20) -> float | None:
    """Calculate current volume relative to the moving average.

    Used by Anti-Bot Intelligence to detect abnormal volume conditions.
    Low volume = likely fakeout / bot trap. High volume = genuine move.

    Args:
        df: OHLCV DataFrame with 'volume' column.
        period: Lookback period for volume moving average.

    Returns:
        Volume ratio (current / avg). None if calculation fails.
    """
    # [SECURE] Null check (Category 5)
    if df is None or df.empty or "volume" not in df.columns:
        return None

    if len(df) < period + 1:
        return None

    current_vol = df["volume"].iloc[-1]
    avg_vol = df["volume"].iloc[-(period + 1):-1].mean()

    # [SECURE] Division by zero prevention (Category 5)
    if pd.isna(avg_vol) or avg_vol <= 0:
        return None

    if pd.isna(current_vol):
        return None

    return float(current_vol / avg_vol)


def calculate_price_momentum(df: pd.DataFrame, period: int = 5) -> float | None:
    """Calculate short-term price momentum (rate of change).

    Used by Anti-Bot Intelligence to detect falling knife scenarios.
    Negative momentum = price still crashing, risky to enter.

    Args:
        df: OHLCV DataFrame with 'close' column.
        period: Lookback period for momentum calculation.

    Returns:
        Price momentum as a ratio (e.g., -0.03 = -3% drop). None if calculation fails.
    """
    # [SECURE] Null check (Category 5)
    if df is None or df.empty or "close" not in df.columns:
        return None

    if len(df) < period + 1:
        return None

    current_close = df["close"].iloc[-1]
    past_close = df["close"].iloc[-(period + 1)]

    # [SECURE] Division by zero prevention (Category 5)
    if pd.isna(past_close) or past_close <= 0 or pd.isna(current_close):
        return None

    return float((current_close - past_close) / past_close)


def calculate_trend_strength(df: pd.DataFrame) -> tuple[float, str]:
    """Calculate trend strength score (0-100) and direction.

    Combines 5 signals to determine how strong the current trend is:
      1. EMA spread 20/50 (0-30 pts): direction + separation strength
      2. Volume vs average (0-20 pts): high volume confirms trend
      3. Price momentum 5-bar (0-25 pts): speed of price movement
      4. Consecutive directional candles (0-15 pts): trend persistence
      5. MACD histogram magnitude (0-10 pts): momentum confirmation

    When score >= threshold (default 50): TREND mode (ride the trend)
    When score < threshold: RANGE mode (mean reversion)

    Args:
        df: OHLCV DataFrame with all required columns.

    Returns:
        Tuple of (score 0-100, direction 'UP'/'DOWN'/'NONE').
    """
    # [SECURE] Null check (Category 5)
    if df is None or df.empty or len(df) < 55:
        return 0.0, "NONE"

    for col in ["close", "high", "low", "volume"]:
        if col not in df.columns:
            return 0.0, "NONE"

    score = 0.0
    direction = "NONE"
    close = df["close"]
    last_price = close.iloc[-1]

    # [SECURE] Division by zero prevention (Category 5)
    if pd.isna(last_price) or last_price <= 0:
        return 0.0, "NONE"

    # --- Signal 1: EMA Spread (0-30 pts) ---
    ema20 = ta.ema(close, length=20)
    ema50 = ta.ema(close, length=50)

    if ema20 is not None and ema50 is not None:
        e20_val = ema20.iloc[-1]
        e50_val = ema50.iloc[-1]
        if not pd.isna(e20_val) and not pd.isna(e50_val) and e50_val > 0:
            spread = (e20_val - e50_val) / e50_val
            ema_score = min(30.0, abs(spread) * 1000)
            score += ema_score
            if spread > 0.005:
                direction = "UP"
            elif spread < -0.005:
                direction = "DOWN"

    # --- Signal 2: Volume vs Average (0-20 pts) ---
    if "volume" in df.columns and len(df) >= 21:
        current_vol = df["volume"].iloc[-1]
        avg_vol = df["volume"].iloc[-21:-1].mean()
        if not pd.isna(current_vol) and not pd.isna(avg_vol) and avg_vol > 0:
            vol_ratio = current_vol / avg_vol
            if vol_ratio > 1.5:
                vol_pts = 20.0
            elif vol_ratio > 1.2:
                vol_pts = 15.0
            elif vol_ratio > 1.0:
                vol_pts = 10.0
            elif vol_ratio > 0.8:
                vol_pts = 5.0
            else:
                vol_pts = 0.0
            # Volume only counts if aligned with trend direction
            if direction != "NONE":
                score += vol_pts

    # --- Signal 3: Price Momentum 5-bar (0-25 pts) ---
    if len(df) >= 6:
        past = close.iloc[-6]
        if not pd.isna(past) and past > 0:
            mom = (last_price - past) / past
            mom_score = min(25.0, abs(mom) * 500)
            # Momentum aligned with trend = add, against = subtract half
            if (direction == "UP" and mom > 0) or (direction == "DOWN" and mom < 0):
                score += mom_score
            elif direction != "NONE":
                score -= mom_score * 0.5

    # --- Signal 4: Consecutive Directional Candles (0-15 pts) ---
    consecutive = 0
    # [SECURE] Bounded loop - max 10 iterations (Category 3)
    lookback = min(10, len(df) - 1)
    for j in range(len(df) - lookback, len(df) - 1):
        if direction == "UP" and close.iloc[j + 1] > close.iloc[j]:
            consecutive += 1
        elif direction == "DOWN" and close.iloc[j + 1] < close.iloc[j]:
            consecutive += 1
    score += min(15.0, consecutive * 2.0)

    # --- Signal 5: MACD Histogram Magnitude (0-10 pts) ---
    macd_result = ta.macd(close, fast=12, slow=26, signal=9)
    if macd_result is not None:
        hist_col = [c for c in macd_result.columns if c.startswith("MACDh")]
        if hist_col:
            mh_val = macd_result[hist_col[0]].iloc[-1]
            if not pd.isna(mh_val) and last_price > 0:
                mh_pct = abs(mh_val) / last_price
                mh_score = min(10.0, mh_pct * 5000)
                if (direction == "UP" and mh_val > 0) or (direction == "DOWN" and mh_val < 0):
                    score += mh_score

    # Clamp score to 0-100
    score = max(0.0, min(100.0, score))

    return score, direction


def calculate_ema_value(df: pd.DataFrame, period: int = 20) -> float | None:
    """Calculate the latest EMA value for a given period.

    Used for pullback detection in trend-following mode.

    Args:
        df: OHLCV DataFrame with 'close' column.
        period: EMA period.

    Returns:
        Latest EMA value, or None if calculation fails.
    """
    # [SECURE] Null check (Category 5)
    if df is None or df.empty or "close" not in df.columns:
        return None
    if len(df) < period + 1:
        return None

    ema = ta.ema(df["close"], length=period)
    if ema is None or ema.empty:
        return None

    val = ema.iloc[-1]
    return float(val) if not pd.isna(val) else None


# --------------------------------------------------
# Security Checklist
# Applied:
#   - Null pointer dereference prevention: input validation on all functions (Category 5)
#   - Uninitialized variable prevention: explicit checks for NaN values (Category 5)
#   - Division by zero prevention: avg_vol, past_close, e50_val checks (Category 5)
#   - Bounded loop: consecutive candle check capped at 10 iterations (Category 3)
# Not Applied:
#   - [WARN] SQL Injection: not applicable - no database used
#   - [WARN] XSS: not applicable - no HTML output
# --------------------------------------------------
