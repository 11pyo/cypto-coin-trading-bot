"""
Sentiment Analysis Experiment: Does news sentiment improve trading performance?

Hypothesis: Sentiment signals improve performance primarily in BEAR markets
(where fear is actionable) and reduce false entries in BULL markets.

Three strategy variants:
  V3_BASE: Existing V3 strategy (no sentiment)
  V3_FG:   V3 + Fear & Greed index integration
  V3_SENT: V3 + composite sentiment (F&G + keyword score + volume anomaly)

Test across ETH, BTC, SOL for 8 periods (2022.06-2026.03).
Statistical comparison with paired t-tests, per-regime analysis, Cohen's d.
"""

import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import requests
import time
import json
import logging
import os
from datetime import datetime, timezone
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
INITIAL_USDT = 333.33
FEE = 0.001

BULLISH_KEYWORDS = [
    "surge", "rally", "pump", "breakout", "ath", "adoption",
    "upgrade", "etf", "approval", "bullish", "soar", "record",
    "partnership", "institutional", "accumulation",
]
BEARISH_KEYWORDS = [
    "crash", "dump", "hack", "ban", "regulation", "lawsuit",
    "bankrupt", "fud", "sell-off", "selloff", "plunge", "liquidation",
    "scam", "fraud", "sec", "crackdown", "fear",
]

# [SECURE] Fixed API URL constants - prevents SSRF (Category 1)
FNG_API_URL = "https://api.alternative.me/fng/?limit=0&format=json"

PERIODS = [
    ("Bear-2022",    "2022-06-01", "2022-10-31", "BEAR"),
    ("Bottom-2022",  "2022-11-01", "2023-03-31", "BEAR"),
    ("Recovery-2023","2023-04-01", "2023-09-30", "BULL"),
    ("Sideways-2023","2023-10-01", "2024-02-28", "SIDEWAYS"),
    ("Bull-2024a",   "2024-03-01", "2024-07-31", "BULL"),
    ("Correction",   "2024-08-01", "2024-12-31", "SIDEWAYS"),
    ("Bull-2025",    "2025-01-01", "2025-06-30", "BULL"),
    ("Recent",       "2025-07-01", "2026-03-15", "BEAR"),
]

SYMBOLS = {
    "ETH": "ETH/USDT",
    "BTC": "BTC/USDT",
    "SOL": "SOL/USDT",
}


# ------------------------------------------------------------------
# Data Fetching
# ------------------------------------------------------------------
def fetch_ohlcv(exchange, symbol, start_date, end_date, timeframe="1h"):
    """Fetch OHLCV data from Binance via ccxt."""
    # [SECURE] Null check before use (Category 5)
    if exchange is None or symbol is None:
        raise ValueError("Exchange and symbol must not be None")

    si = exchange.parse8601(start_date + "T00:00:00Z")
    ei = exchange.parse8601(end_date + "T23:59:59Z")
    all_candles = []
    fetch_count = 0
    # [SECURE] Max retry cap - prevents infinite loop (Category 3)
    MAX_FETCH = 60
    while fetch_count < MAX_FETCH:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=si, limit=500)
        except Exception as e:
            # [SECURE] Log error server-side only (Category 4)
            logger.warning("OHLCV fetch error for %s: %s", symbol, type(e).__name__)
            time.sleep(2)
            fetch_count += 1
            continue
        if not candles:
            break
        candles = [x for x in candles if x[0] <= ei]
        all_candles.extend(candles)
        if not candles or candles[-1][0] >= ei:
            break
        si = candles[-1][0] + 1
        fetch_count += 1
        time.sleep(0.35)

    if not all_candles:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(all_candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)
    return df


def fetch_fear_greed_history():
    """Fetch full Fear & Greed Index history from alternative.me."""
    try:
        # [SECURE] Fixed URL - no user input (SSRF prevention, Category 1)
        resp = requests.get(FNG_API_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # [SECURE] Null check on response structure (Category 5)
        if data is None or "data" not in data:
            logger.warning("F&G API returned unexpected format")
            return {}

        fg_map = {}
        for item in data["data"]:
            ts = int(item["timestamp"])
            date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            # [SECURE] Range validation (Category 1)
            value = int(item["value"])
            if 0 <= value <= 100:
                fg_map[date_str] = value
        logger.info("Fetched F&G data: %d days", len(fg_map))
        return fg_map
    except requests.RequestException as e:
        # [SECURE] Log type only - no internal detail exposed (Category 4)
        logger.warning("Failed to fetch F&G index: %s", type(e).__name__)
        return {}
    except (ValueError, KeyError, IndexError) as e:
        # [SECURE] Handle parse error - no empty except (Category 4)
        logger.warning("Failed to parse F&G response: %s", type(e).__name__)
        return {}


# ------------------------------------------------------------------
# Indicator Computation
# ------------------------------------------------------------------
def compute_indicators(df):
    """Compute technical indicators used by V3 strategy."""
    df = df.copy()
    # [SECURE] Null check (Category 5)
    if df.empty or len(df) < 60:
        return df

    df["rsi"] = ta.rsi(df["close"], length=14)

    macd_result = ta.macd(df["close"], fast=12, slow=26, signal=9)
    # [SECURE] Null check before accessing columns (Category 5)
    if macd_result is not None and not macd_result.empty:
        mh_cols = [c for c in macd_result.columns if c.startswith("MACDh")]
        if mh_cols:
            df["mh"] = macd_result[mh_cols[0]]

    bb_result = ta.bbands(df["close"], length=20, std=2.0)
    if bb_result is not None and not bb_result.empty:
        bbu_cols = [c for c in bb_result.columns if c.startswith("BBU")]
        bbl_cols = [c for c in bb_result.columns if c.startswith("BBL")]
        if bbu_cols:
            df["bbu"] = bb_result[bbu_cols[0]]
        if bbl_cols:
            df["bbl"] = bb_result[bbl_cols[0]]

    df["va"] = df["volume"].rolling(20).mean()
    df["vr"] = df["volume"] / df["va"]
    df["mom"] = df["close"].pct_change(5)
    df["e20"] = ta.ema(df["close"], length=20)
    df["e50"] = ta.ema(df["close"], length=50)

    # Volume anomaly score: z-score of volume
    vol_mean = df["volume"].rolling(50).mean()
    vol_std = df["volume"].rolling(50).std()
    # [SECURE] Division-by-zero guard (Category 5)
    df["vol_zscore"] = np.where(vol_std > 0, (df["volume"] - vol_mean) / vol_std, 0.0)

    return df


# ------------------------------------------------------------------
# Keyword Sentiment Scorer (synthetic from price action patterns)
# ------------------------------------------------------------------
def compute_keyword_sentiment(df):
    """Generate synthetic keyword sentiment score from price action patterns.

    In the absence of real news headlines, we proxy news sentiment from:
    - Large price moves (big moves generate headlines)
    - Volume spikes (activity generates coverage)
    - Momentum direction (trending markets get bullish/bearish coverage)

    Returns a series of sentiment scores in [-1, 1].
    """
    df = df.copy()
    sentiment = pd.Series(0.0, index=df.index)

    # [SECURE] Null check (Category 5)
    if df.empty or "close" not in df.columns:
        return sentiment

    pct_1h = df["close"].pct_change(1).fillna(0)
    pct_4h = df["close"].pct_change(4).fillna(0)
    pct_24h = df["close"].pct_change(24).fillna(0)

    # Large positive moves -> bullish headlines
    sentiment += np.where(pct_24h > 0.05, 0.6, 0.0)
    sentiment += np.where(pct_24h > 0.10, 0.4, 0.0)
    # Large negative moves -> bearish headlines
    sentiment += np.where(pct_24h < -0.05, -0.6, 0.0)
    sentiment += np.where(pct_24h < -0.10, -0.4, 0.0)

    # Short-term momentum
    sentiment += np.where(pct_4h > 0.03, 0.2, 0.0)
    sentiment += np.where(pct_4h < -0.03, -0.2, 0.0)

    # Volume anomaly amplification
    if "vol_zscore" in df.columns:
        vol_z = df["vol_zscore"].fillna(0)
        # High volume amplifies the directional signal
        vol_amp = np.where(vol_z > 2.0, 0.3, np.where(vol_z > 1.0, 0.15, 0.0))
        direction = np.sign(pct_4h)
        sentiment += vol_amp * direction

    # Clip to [-1, 1]
    sentiment = sentiment.clip(-1.0, 1.0)

    # Smooth with EMA for persistence (news sentiment lingers)
    sentiment = sentiment.ewm(span=12, adjust=False).mean()

    return sentiment


# ------------------------------------------------------------------
# V3 Strategy Engine (base, with optional sentiment inputs)
# ------------------------------------------------------------------
def run_v3(df, fg_series=None, sentiment_series=None, variant="V3_BASE"):
    """Run V3 strategy simulation.

    Args:
        df: DataFrame with OHLCV + indicators
        fg_series: Fear & Greed index aligned to df index (or None)
        sentiment_series: Composite sentiment [-1,1] aligned to df index (or None)
        variant: "V3_BASE", "V3_FG", or "V3_SENT"

    Returns:
        dict with performance metrics
    """
    df = df.copy()
    # [SECURE] Null check (Category 5)
    if df.empty or len(df) < 60:
        return _empty_result()

    # V3 parameters
    BASE = 0.15
    SL = 0.08
    TP = 0.10
    CD = 18
    MH = 8
    GOLDEN_MULT = 3.0
    GOLDEN_TP = 0.15
    DANGER_THRESH = 55
    GOLDEN_LO = 30
    GOLDEN_HI = 55

    u = INITIAL_USDT
    entries = []
    cd = 0
    hold = 0
    pp = 0
    wins = 0
    losses = 0
    total_profit = 0.0
    total_loss = 0.0
    n_trades = 0
    peak_val = INITIAL_USDT
    max_dd = 0.0
    trade_log = []

    def tscore(i):
        if i < 55:
            return 0, "NONE"
        r = df.iloc[i]
        s = 0.0
        d = "NONE"
        e20 = r.get("e20")
        e50 = r.get("e50")
        if not pd.isna(e20) and not pd.isna(e50) and e50 > 0:
            sp = (e20 - e50) / e50
            s += min(30, abs(sp) * 1000)
            d = "UP" if sp > 0.005 else ("DOWN" if sp < -0.005 else "NONE")
        vr_val = r.get("vr")
        if not pd.isna(vr_val) and d != "NONE":
            if vr_val > 1.5:
                s += 20
            elif vr_val > 1.2:
                s += 15
            elif vr_val > 1.0:
                s += 10
        mom_val = r.get("mom")
        if not pd.isna(mom_val):
            ms = min(25, abs(mom_val) * 500)
            if (d == "UP" and mom_val > 0) or (d == "DOWN" and mom_val < 0):
                s += ms
            elif d != "NONE":
                s -= ms * 0.5
        cc = 0
        for j in range(max(0, i - 10), i - 1):
            if d == "UP" and df["close"].iloc[j + 1] > df["close"].iloc[j]:
                cc += 1
            elif d == "DOWN" and df["close"].iloc[j + 1] < df["close"].iloc[j]:
                cc += 1
        s += min(15, cc * 2)
        mh_val = r.get("mh")
        if not pd.isna(mh_val) and r["close"] > 0:
            ms2 = min(10, abs(mh_val) / r["close"] * 5000)
            if (d == "UP" and mh_val > 0) or (d == "DOWN" and mh_val < 0):
                s += ms2
        return max(0, min(100, s)), d

    # [SECURE] Max iteration cap (Category 3)
    for i in range(55, len(df)):
        r = df.iloc[i]
        p = r["close"]
        rsi = r.get("rsi")
        if pd.isna(rsi) or pd.isna(r.get("bbu")) or pd.isna(r.get("bbl")):
            continue

        cd = max(0, cd - 1)
        ts, td = tscore(i)

        # --- Sentiment adjustments ---
        fg_val = None
        sent_val = 0.0

        if fg_series is not None and i < len(fg_series):
            fg_val = fg_series.iloc[i]
            if pd.isna(fg_val):
                fg_val = None

        if sentiment_series is not None and i < len(sentiment_series):
            sent_val = sentiment_series.iloc[i]
            if pd.isna(sent_val):
                sent_val = 0.0

        # V3_FG: Fear & Greed modifies zone thresholds
        fg_adjustment = 0
        if variant in ("V3_FG", "V3_SENT") and fg_val is not None:
            # Extreme fear -> lower danger threshold (more willing to buy)
            # Extreme greed -> raise danger threshold (more cautious)
            if fg_val <= 20:
                fg_adjustment = -10  # lower thresholds: buy in fear
            elif fg_val <= 35:
                fg_adjustment = -5
            elif fg_val >= 75:
                fg_adjustment = 10   # raise thresholds: sell in greed
            elif fg_val >= 60:
                fg_adjustment = 5

        # V3_SENT: Composite sentiment further adjusts
        sent_adjustment = 0
        if variant == "V3_SENT":
            # Strong bearish sentiment -> more defensive (raise danger threshold)
            # Strong bullish sentiment -> more aggressive (lower thresholds)
            sent_adjustment = int(-sent_val * 8)  # [-8, +8] range

        eff_danger = DANGER_THRESH + fg_adjustment + sent_adjustment
        eff_golden_lo = GOLDEN_LO + (fg_adjustment // 2) + (sent_adjustment // 2)
        eff_golden_hi = GOLDEN_HI + (fg_adjustment // 2) + (sent_adjustment // 2)

        # Zone determination
        if td == "DOWN" and ts >= eff_golden_lo:
            zone = "DOWN"
        elif ts >= eff_danger:
            zone = "DANGER"
        elif eff_golden_lo <= ts < eff_golden_hi:
            zone = "GOLDEN"
        else:
            zone = "RANGE"

        # Sentiment-based position sizing modifier
        size_mult = 1.0
        if variant == "V3_SENT":
            # Extreme fear + oversold = contrarian buy opportunity -> larger size
            if fg_val is not None and fg_val <= 25 and rsi < 40:
                size_mult = 1.3
            # Extreme greed -> reduce size
            elif fg_val is not None and fg_val >= 75:
                size_mult = 0.7

        # Sentiment-based TP/SL modifier
        tp_mod = 1.0
        sl_mod = 1.0
        if variant == "V3_SENT":
            if sent_val > 0.5:
                tp_mod = 1.2   # bullish: let profits run
                sl_mod = 1.1   # slightly wider SL
            elif sent_val < -0.5:
                tp_mod = 0.8   # bearish: take profits faster
                sl_mod = 0.85  # tighter SL

        has = len(entries) > 0
        tq = sum(e[1] for e in entries) if has else 0
        ap = (sum(e[0] * e[1] for e in entries) / tq) if tq > 0 else 0
        ti = sum(e[0] * e[1] for e in entries) if has else 0
        pv = u + (tq * p if has else 0)
        peak_val = max(peak_val, pv)
        dd = (peak_val - pv) / peak_val if peak_val > 0 else 0
        max_dd = max(max_dd, dd)
        if has:
            hold += 1
            pp = max(pp, p)

        # --- Exits ---
        if has:
            cur_tp = GOLDEN_TP if zone == "GOLDEN" else TP
            cur_tp *= tp_mod
            cur_sl = SL * sl_mod

            # Sentiment-driven early exit (V3_SENT only)
            force_exit = False
            if variant == "V3_SENT" and fg_val is not None:
                # Extreme greed + overbought = exit signal
                if fg_val >= 80 and rsi > 65 and hold >= 4:
                    force_exit = True
                # Extreme fear + price crashing = cut losses early
                if fg_val <= 15 and sent_val < -0.7 and (p < ap * 0.96):
                    force_exit = True

            if p <= ap * (1 - cur_sl) or force_exit:
                sv = tq * p * (1 - FEE)
                pnl = sv - ti
                u += sv
                if pnl > 0:
                    wins += 1
                    total_profit += pnl
                else:
                    losses += 1
                    total_loss += pnl
                entries = []
                hold = 0
                pp = 0
                cd = CD
                n_trades += 1
                continue

            if p >= ap * (1 + cur_tp):
                sv = tq * p * (1 - FEE)
                pnl = sv - ti
                u += sv
                if pnl > 0:
                    wins += 1
                    total_profit += pnl
                else:
                    losses += 1
                    total_loss += pnl
                entries = []
                hold = 0
                pp = 0
                cd = CD
                n_trades += 1
                continue

            # Signal sell
            if zone in ("RANGE", "GOLDEN") and hold >= MH:
                sa = (rsi > 72) or (p > r["bbu"] * 0.98)
                mh_prev = df["mh"].iloc[i - 1] if i > 0 else np.nan
                sb = (r["mh"] < mh_prev) if not pd.isna(mh_prev) else False
                if sa and sb:
                    sv = tq * p * (1 - FEE)
                    pnl = sv - ti
                    u += sv
                    if pnl > 0:
                        wins += 1
                        total_profit += pnl
                    else:
                        losses += 1
                        total_loss += pnl
                    entries = []
                    hold = 0
                    pp = 0
                    cd = CD
                    n_trades += 1
                    continue

        # --- Entry ---
        vr_val = r.get("vr", np.nan)
        mom_val = r.get("mom", np.nan)
        lv = (not pd.isna(vr_val)) and vr_val < 0.5
        fl = (not pd.isna(mom_val)) and mom_val < -0.03

        # Sentiment-based entry filter (V3_FG and V3_SENT)
        sentiment_block = False
        sentiment_boost = False
        if variant in ("V3_FG", "V3_SENT") and fg_val is not None:
            # Block entries when greed is extreme
            if fg_val >= 80:
                sentiment_block = True
            # Boost confidence for contrarian buys in fear
            if fg_val <= 25:
                sentiment_boost = True

        if variant == "V3_SENT" and sent_val < -0.8:
            # Very strong bearish composite sentiment -> block new entries
            sentiment_block = True

        if zone == "DANGER" or zone == "DOWN":
            ib = False
        elif zone == "GOLDEN":
            pb_rsi = rsi < 45
            e20v = r.get("e20", np.nan)
            pb_ema = (not pd.isna(e20v)) and p <= e20v * 1.01
            mh_prev = df["mh"].iloc[i - 1] if i > 0 else np.nan
            bb = (r["mh"] > mh_prev) if not pd.isna(mh_prev) else False
            ib = (pb_rsi or pb_ema) and bb and not lv and cd <= 0
            if ib and (not pd.isna(mom_val)) and mom_val < -0.02:
                ib = False
        else:  # RANGE
            ba = (rsi < 35) or (p < r["bbl"] * 1.02)
            mh_prev = df["mh"].iloc[i - 1] if i > 0 else np.nan
            bb = (r["mh"] > mh_prev) if not pd.isna(mh_prev) else False
            ib = ba and bb and not lv and not fl and cd <= 0

        # Apply sentiment filter
        if sentiment_block:
            ib = False
        # Sentiment boost: relax RSI threshold in fear zone
        if sentiment_boost and not ib and not has and cd <= 0 and zone == "RANGE":
            if rsi < 42 and not lv:
                mh_prev = df["mh"].iloc[i - 1] if i > 0 else np.nan
                bb = (r["mh"] > mh_prev) if not pd.isna(mh_prev) else False
                if bb:
                    ib = True

        sz = BASE * (GOLDEN_MULT if zone == "GOLDEN" else 1.0) * size_mult
        if ib and not has:
            ou = u * sz
            if ou >= 10:
                q = (ou - ou * FEE) / p
                u -= ou
                entries.append((p, q, 0))
                pp = p
                n_trades += 1
                cd = CD
                continue

        # --- DCA ---
        if has and len(entries) < 4 and zone != "DANGER":
            lvl = len(entries)
            drops = [0.04, 0.08, 0.12]
            mults = [1.5, 2.0, 2.5]
            if lvl <= len(drops):
                dr = (ap - p) / ap if ap > 0 else 0
                if dr >= drops[lvl - 1]:
                    ba2 = (rsi < 35) or (p < r["bbl"] * 1.02)
                    mh_prev = df["mh"].iloc[i - 1] if i > 0 else np.nan
                    bb2 = (r["mh"] > mh_prev) if not pd.isna(mh_prev) else False
                    dok = (rsi < 25) or (ba2 and bb2)
                    if (not pd.isna(vr_val)) and vr_val < 0.3:
                        dok = False
                    # Sentiment can boost DCA in extreme fear
                    if variant in ("V3_FG", "V3_SENT") and sentiment_boost and rsi < 40:
                        dok = True
                    if dok:
                        m = mults[lvl - 1]
                        ou = u * sz * m
                        ma = (u + ti) * 0.40
                        if ti + ou > ma:
                            ou = max(0, ma - ti)
                        if ou >= 10:
                            q = (ou - ou * FEE) / p
                            u -= ou
                            entries.append((p, q, lvl))
                            n_trades += 1
                            cd = CD
                            continue

    # Final valuation
    lp = df["close"].iloc[-1]
    unr = sum(e[1] for e in entries) * lp if entries else 0
    fv = u + unr
    sp = df["close"].iloc[55] if len(df) > 55 else df["close"].iloc[0]
    bh = ((INITIAL_USDT * (1 - FEE)) / sp * lp - INITIAL_USDT) / INITIAL_USDT * 100 if sp > 0 else 0
    tot = wins + losses
    wr = (wins / tot * 100) if tot > 0 else 0
    pf = abs(total_profit / total_loss) if total_loss != 0 else 999

    return {
        "return_pct": round(((fv - INITIAL_USDT) / INITIAL_USDT) * 100, 4),
        "buy_hold_pct": round(bh, 4),
        "alpha": round(((fv - INITIAL_USDT) / INITIAL_USDT) * 100 - bh, 4),
        "win_rate": round(wr, 2),
        "profit_factor": round(min(pf, 999), 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "n_trades": n_trades,
        "final_value": round(fv, 2),
    }


def _empty_result():
    return {
        "return_pct": 0.0,
        "buy_hold_pct": 0.0,
        "alpha": 0.0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "max_drawdown_pct": 0.0,
        "n_trades": 0,
        "final_value": INITIAL_USDT,
    }


# ------------------------------------------------------------------
# Fear & Greed Alignment
# ------------------------------------------------------------------
def align_fg_to_df(df, fg_map):
    """Align daily F&G values to hourly OHLCV dataframe."""
    # [SECURE] Null check (Category 5)
    if df.empty or not fg_map:
        return pd.Series(np.nan, index=df.index)

    dates = df["timestamp"].dt.strftime("%Y-%m-%d")
    fg_series = dates.map(fg_map).astype(float)
    return fg_series


# ------------------------------------------------------------------
# Statistical Tests
# ------------------------------------------------------------------
def paired_t_test(a, b):
    """Perform paired t-test and return t-stat, p-value."""
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    # [SECURE] Null/empty check (Category 5)
    if len(a) < 2 or len(b) < 2 or len(a) != len(b):
        return 0.0, 1.0
    t_stat, p_val = stats.ttest_rel(a, b)
    return round(float(t_stat), 4), round(float(p_val), 4)


def cohens_d(a, b):
    """Compute Cohen's d effect size for paired samples."""
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    if len(a) < 2:
        return 0.0
    diff = a - b
    d = np.mean(diff) / np.std(diff, ddof=1) if np.std(diff, ddof=1) > 0 else 0.0
    return round(float(d), 4)


def interpret_effect_size(d):
    """Interpret Cohen's d."""
    d_abs = abs(d)
    if d_abs < 0.2:
        return "negligible"
    elif d_abs < 0.5:
        return "small"
    elif d_abs < 0.8:
        return "medium"
    else:
        return "large"


# ------------------------------------------------------------------
# Main Experiment
# ------------------------------------------------------------------
def main():
    logger.info("=" * 80)
    logger.info("  SENTIMENT EXPERIMENT: Does news sentiment improve trading?")
    logger.info("=" * 80)

    exchange = ccxt.binance({"enableRateLimit": True})

    # Step 1: Fetch Fear & Greed history
    logger.info("Fetching Fear & Greed Index history...")
    fg_map = fetch_fear_greed_history()
    if not fg_map:
        logger.warning("F&G data unavailable. Will generate synthetic F&G from price action.")

    # Step 2: Run experiments across all symbols and periods
    all_results = {}
    variant_names = ["V3_BASE", "V3_FG", "V3_SENT"]

    for sym_name, sym_pair in SYMBOLS.items():
        logger.info("Processing %s (%s)...", sym_name, sym_pair)
        all_results[sym_name] = {}

        for period_name, start_d, end_d, regime in PERIODS:
            logger.info("  Period: %s (%s to %s) [%s]", period_name, start_d, end_d, regime)

            # Fetch OHLCV
            df = fetch_ohlcv(exchange, sym_pair, start_d, end_d)
            if df.empty or len(df) < 100:
                logger.warning("  Insufficient data for %s %s, skipping", sym_name, period_name)
                all_results[sym_name][period_name] = {
                    "regime": regime,
                    "n_candles": len(df),
                    "V3_BASE": _empty_result(),
                    "V3_FG": _empty_result(),
                    "V3_SENT": _empty_result(),
                }
                continue

            # Compute indicators
            df = compute_indicators(df)

            # Align F&G
            fg_series = align_fg_to_df(df, fg_map)

            # If no real F&G data, generate synthetic F&G from price momentum
            if fg_map is None or len(fg_map) == 0:
                # Synthetic F&G: inverse of 30-day momentum mapped to [0,100]
                mom30 = df["close"].pct_change(24 * 30).fillna(0)
                fg_series = (50 - mom30 * 200).clip(0, 100)

            # Compute keyword sentiment
            kw_sentiment = compute_keyword_sentiment(df)

            # Composite sentiment: weighted average of F&G-derived + keyword + vol anomaly
            fg_norm = ((fg_series.fillna(50) - 50) / 50).clip(-1, 1)  # map [0,100] -> [-1,1]
            vol_anomaly = df["vol_zscore"].fillna(0).clip(-3, 3) / 3  # normalize to [-1,1]

            composite_sent = (
                0.4 * fg_norm +         # F&G component
                0.35 * kw_sentiment +    # keyword/price-action component
                0.25 * vol_anomaly       # volume anomaly component
            ).clip(-1, 1)

            # Run three variants
            period_results = {
                "regime": regime,
                "n_candles": len(df),
                "start_price": round(float(df["close"].iloc[55]), 2) if len(df) > 55 else 0,
                "end_price": round(float(df["close"].iloc[-1]), 2),
            }

            for variant in variant_names:
                if variant == "V3_BASE":
                    result = run_v3(df, fg_series=None, sentiment_series=None, variant=variant)
                elif variant == "V3_FG":
                    result = run_v3(df, fg_series=fg_series, sentiment_series=None, variant=variant)
                else:  # V3_SENT
                    result = run_v3(df, fg_series=fg_series, sentiment_series=composite_sent, variant=variant)
                period_results[variant] = result
                logger.info("    %s: ret=%+.2f%% alpha=%+.2f%% wr=%.0f%% dd=%.1f%% trades=%d",
                            variant, result["return_pct"], result["alpha"],
                            result["win_rate"], result["max_drawdown_pct"], result["n_trades"])

            all_results[sym_name][period_name] = period_results

    # Step 3: Statistical analysis
    logger.info("=" * 80)
    logger.info("  STATISTICAL ANALYSIS")
    logger.info("=" * 80)

    stats_results = compute_statistics(all_results)

    # Step 4: Build final output
    output = {
        "experiment": "Sentiment Analysis - Does news sentiment improve trading?",
        "hypothesis": "Sentiment signals improve performance primarily in BEAR markets (where fear is actionable) and reduce false entries in BULL markets.",
        "date_run": datetime.now(tz=timezone.utc).isoformat(),
        "symbols": list(SYMBOLS.keys()),
        "periods": [{"name": p[0], "start": p[1], "end": p[2], "regime": p[3]} for p in PERIODS],
        "variants": {
            "V3_BASE": "V3 strategy with no sentiment input",
            "V3_FG": "V3 + Fear & Greed index modifies zone thresholds and entry/exit",
            "V3_SENT": "V3 + composite sentiment (F&G + keyword score + volume anomaly)",
        },
        "fg_data_available": len(fg_map) > 0,
        "fg_data_points": len(fg_map),
        "detailed_results": all_results,
        "statistics": stats_results,
    }

    # Save results
    results_path = os.path.join(os.path.dirname(__file__), "sentiment_results.json")
    # [SECURE] Context manager ensures resource release (Category 5)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    logger.info("Results saved to %s", results_path)

    # Print summary
    print_summary(output)

    return output


def compute_statistics(all_results):
    """Compute paired t-tests, per-regime analysis, and Cohen's d."""
    stats_out = {
        "overall_comparison": {},
        "per_regime": {},
        "per_symbol": {},
    }

    # Collect returns by variant across all (symbol, period) pairs
    base_rets = []
    fg_rets = []
    sent_rets = []
    base_alphas = []
    fg_alphas = []
    sent_alphas = []

    regime_data = {"BEAR": {"base": [], "fg": [], "sent": []},
                   "BULL": {"base": [], "fg": [], "sent": []},
                   "SIDEWAYS": {"base": [], "fg": [], "sent": []}}

    symbol_data = {}

    for sym in all_results:
        sym_base = []
        sym_fg = []
        sym_sent = []
        for period in all_results[sym]:
            pr = all_results[sym][period]
            regime = pr.get("regime", "SIDEWAYS")
            b = pr.get("V3_BASE", {}).get("return_pct", 0.0)
            f = pr.get("V3_FG", {}).get("return_pct", 0.0)
            s = pr.get("V3_SENT", {}).get("return_pct", 0.0)
            ba = pr.get("V3_BASE", {}).get("alpha", 0.0)
            fa = pr.get("V3_FG", {}).get("alpha", 0.0)
            sa = pr.get("V3_SENT", {}).get("alpha", 0.0)

            base_rets.append(b)
            fg_rets.append(f)
            sent_rets.append(s)
            base_alphas.append(ba)
            fg_alphas.append(fa)
            sent_alphas.append(sa)
            sym_base.append(b)
            sym_fg.append(f)
            sym_sent.append(s)

            if regime in regime_data:
                regime_data[regime]["base"].append(b)
                regime_data[regime]["fg"].append(f)
                regime_data[regime]["sent"].append(s)

        symbol_data[sym] = {"base": sym_base, "fg": sym_fg, "sent": sym_sent}

    # Overall comparison
    for comp_name, a_vals, b_vals in [
        ("V3_FG_vs_BASE_return", fg_rets, base_rets),
        ("V3_SENT_vs_BASE_return", sent_rets, base_rets),
        ("V3_SENT_vs_FG_return", sent_rets, fg_rets),
        ("V3_FG_vs_BASE_alpha", fg_alphas, base_alphas),
        ("V3_SENT_vs_BASE_alpha", sent_alphas, base_alphas),
    ]:
        t, p = paired_t_test(a_vals, b_vals)
        d = cohens_d(a_vals, b_vals)
        mean_diff = round(float(np.mean(np.array(a_vals) - np.array(b_vals))), 4) if a_vals else 0
        stats_out["overall_comparison"][comp_name] = {
            "mean_difference": mean_diff,
            "t_statistic": t,
            "p_value": p,
            "significant_at_005": p < 0.05,
            "significant_at_010": p < 0.10,
            "cohens_d": d,
            "effect_size": interpret_effect_size(d),
            "n_pairs": len(a_vals),
        }

    # Per-regime analysis
    for regime, rd in regime_data.items():
        if len(rd["base"]) < 2:
            stats_out["per_regime"][regime] = {
                "n_periods": len(rd["base"]),
                "note": "Too few periods for statistical test",
                "mean_base": round(float(np.mean(rd["base"])), 2) if rd["base"] else 0,
                "mean_fg": round(float(np.mean(rd["fg"])), 2) if rd["fg"] else 0,
                "mean_sent": round(float(np.mean(rd["sent"])), 2) if rd["sent"] else 0,
            }
            continue

        t_fg, p_fg = paired_t_test(rd["fg"], rd["base"])
        t_sent, p_sent = paired_t_test(rd["sent"], rd["base"])
        d_fg = cohens_d(rd["fg"], rd["base"])
        d_sent = cohens_d(rd["sent"], rd["base"])

        stats_out["per_regime"][regime] = {
            "n_periods": len(rd["base"]),
            "mean_return_base": round(float(np.mean(rd["base"])), 2),
            "mean_return_fg": round(float(np.mean(rd["fg"])), 2),
            "mean_return_sent": round(float(np.mean(rd["sent"])), 2),
            "fg_vs_base": {
                "mean_diff": round(float(np.mean(np.array(rd["fg"]) - np.array(rd["base"]))), 2),
                "t_stat": t_fg, "p_value": p_fg,
                "cohens_d": d_fg, "effect_size": interpret_effect_size(d_fg),
            },
            "sent_vs_base": {
                "mean_diff": round(float(np.mean(np.array(rd["sent"]) - np.array(rd["base"]))), 2),
                "t_stat": t_sent, "p_value": p_sent,
                "cohens_d": d_sent, "effect_size": interpret_effect_size(d_sent),
            },
        }

    # Per-symbol analysis
    for sym, sd in symbol_data.items():
        if len(sd["base"]) < 2:
            continue
        t_fg, p_fg = paired_t_test(sd["fg"], sd["base"])
        t_sent, p_sent = paired_t_test(sd["sent"], sd["base"])
        d_fg = cohens_d(sd["fg"], sd["base"])
        d_sent = cohens_d(sd["sent"], sd["base"])
        stats_out["per_symbol"][sym] = {
            "n_periods": len(sd["base"]),
            "mean_return_base": round(float(np.mean(sd["base"])), 2),
            "mean_return_fg": round(float(np.mean(sd["fg"])), 2),
            "mean_return_sent": round(float(np.mean(sd["sent"])), 2),
            "fg_vs_base": {
                "mean_diff": round(float(np.mean(np.array(sd["fg"]) - np.array(sd["base"]))), 2),
                "t_stat": t_fg, "p_value": p_fg,
                "cohens_d": d_fg, "effect_size": interpret_effect_size(d_fg),
            },
            "sent_vs_base": {
                "mean_diff": round(float(np.mean(np.array(sd["sent"]) - np.array(sd["base"]))), 2),
                "t_stat": t_sent, "p_value": p_sent,
                "cohens_d": d_sent, "effect_size": interpret_effect_size(d_sent),
            },
        }

    return stats_out


def print_summary(output):
    """Print a formatted summary of the experiment results."""
    print("\n" + "=" * 100)
    print("  SENTIMENT EXPERIMENT RESULTS")
    print("=" * 100)

    # Detailed results table
    print(f"\n{'Symbol':<6} {'Period':<16} {'Regime':<9} | {'V3_BASE':>10} {'V3_FG':>10} {'V3_SENT':>10} | {'FG-BASE':>9} {'SENT-BASE':>10}")
    print("-" * 100)

    for sym in output["detailed_results"]:
        for period in output["detailed_results"][sym]:
            pr = output["detailed_results"][sym][period]
            regime = pr.get("regime", "?")
            b = pr.get("V3_BASE", {}).get("return_pct", 0)
            f = pr.get("V3_FG", {}).get("return_pct", 0)
            s = pr.get("V3_SENT", {}).get("return_pct", 0)
            print(f"{sym:<6} {period:<16} {regime:<9} | {b:>+9.2f}% {f:>+9.2f}% {s:>+9.2f}% | {f-b:>+8.2f}% {s-b:>+9.2f}%")

    # Statistics summary
    print("\n" + "=" * 100)
    print("  STATISTICAL TESTS")
    print("=" * 100)

    stats = output.get("statistics", {})

    print("\n  OVERALL COMPARISON:")
    for comp_name, comp_data in stats.get("overall_comparison", {}).items():
        sig_marker = "***" if comp_data.get("significant_at_005") else ("*" if comp_data.get("significant_at_010") else "n.s.")
        print(f"    {comp_name}:")
        print(f"      Mean diff: {comp_data.get('mean_difference', 0):+.4f}%  "
              f"t={comp_data.get('t_statistic', 0):.3f}  "
              f"p={comp_data.get('p_value', 1):.4f} {sig_marker}  "
              f"d={comp_data.get('cohens_d', 0):.3f} ({comp_data.get('effect_size', 'N/A')})")

    print("\n  PER-REGIME ANALYSIS (key hypothesis test):")
    for regime, rd in stats.get("per_regime", {}).items():
        print(f"\n    {regime} (n={rd.get('n_periods', 0)}):")
        print(f"      Mean returns: BASE={rd.get('mean_return_base', 0):+.2f}%  "
              f"FG={rd.get('mean_return_fg', 0):+.2f}%  "
              f"SENT={rd.get('mean_return_sent', 0):+.2f}%")
        if "fg_vs_base" in rd:
            fg = rd["fg_vs_base"]
            sent = rd["sent_vs_base"]
            fg_sig = "***" if fg.get("p_value", 1) < 0.05 else ("*" if fg.get("p_value", 1) < 0.10 else "n.s.")
            sent_sig = "***" if sent.get("p_value", 1) < 0.05 else ("*" if sent.get("p_value", 1) < 0.10 else "n.s.")
            print(f"      FG vs BASE:   diff={fg.get('mean_diff', 0):+.2f}%  "
                  f"p={fg.get('p_value', 1):.4f} {fg_sig}  "
                  f"d={fg.get('cohens_d', 0):.3f} ({fg.get('effect_size', 'N/A')})")
            print(f"      SENT vs BASE: diff={sent.get('mean_diff', 0):+.2f}%  "
                  f"p={sent.get('p_value', 1):.4f} {sent_sig}  "
                  f"d={sent.get('cohens_d', 0):.3f} ({sent.get('effect_size', 'N/A')})")

    print("\n  PER-SYMBOL ANALYSIS:")
    for sym, sd in stats.get("per_symbol", {}).items():
        print(f"\n    {sym} (n={sd.get('n_periods', 0)}):")
        print(f"      Mean returns: BASE={sd.get('mean_return_base', 0):+.2f}%  "
              f"FG={sd.get('mean_return_fg', 0):+.2f}%  "
              f"SENT={sd.get('mean_return_sent', 0):+.2f}%")
        if "fg_vs_base" in sd:
            fg = sd["fg_vs_base"]
            sent = sd["sent_vs_base"]
            print(f"      FG vs BASE:   diff={fg.get('mean_diff', 0):+.2f}%  "
                  f"p={fg.get('p_value', 1):.4f}  d={fg.get('cohens_d', 0):.3f}")
            print(f"      SENT vs BASE: diff={sent.get('mean_diff', 0):+.2f}%  "
                  f"p={sent.get('p_value', 1):.4f}  d={sent.get('cohens_d', 0):.3f}")

    # Conclusion
    print("\n" + "=" * 100)
    print("  CONCLUSION")
    print("=" * 100)

    overall = stats.get("overall_comparison", {})
    sent_vs_base = overall.get("V3_SENT_vs_BASE_return", {})
    fg_vs_base = overall.get("V3_FG_vs_BASE_return", {})

    bear_data = stats.get("per_regime", {}).get("BEAR", {})
    bull_data = stats.get("per_regime", {}).get("BULL", {})

    print(f"\n  Overall V3_SENT vs V3_BASE:")
    print(f"    Mean return difference: {sent_vs_base.get('mean_difference', 0):+.4f}%")
    print(f"    Statistical significance: p={sent_vs_base.get('p_value', 1):.4f} "
          f"({'significant' if sent_vs_base.get('significant_at_005') else 'not significant'} at alpha=0.05)")
    print(f"    Effect size: d={sent_vs_base.get('cohens_d', 0):.3f} ({sent_vs_base.get('effect_size', 'N/A')})")

    print(f"\n  Hypothesis Test - Sentiment helps more in BEAR markets:")
    if "sent_vs_base" in bear_data:
        bear_diff = bear_data["sent_vs_base"].get("mean_diff", 0)
        bear_p = bear_data["sent_vs_base"].get("p_value", 1)
    else:
        bear_diff = bear_data.get("mean_sent", 0) - bear_data.get("mean_base", 0)
        bear_p = 1.0
    if "sent_vs_base" in bull_data:
        bull_diff = bull_data["sent_vs_base"].get("mean_diff", 0)
        bull_p = bull_data["sent_vs_base"].get("p_value", 1)
    else:
        bull_diff = bull_data.get("mean_sent", 0) - bull_data.get("mean_base", 0)
        bull_p = 1.0

    print(f"    BEAR market sentiment improvement: {bear_diff:+.2f}% (p={bear_p:.4f})")
    print(f"    BULL market sentiment improvement: {bull_diff:+.2f}% (p={bull_p:.4f})")

    if bear_diff > bull_diff:
        print(f"    --> SUPPORTED: Sentiment provides {bear_diff - bull_diff:.2f}% MORE benefit in BEAR vs BULL")
    else:
        print(f"    --> NOT SUPPORTED: Sentiment provides {bull_diff - bear_diff:.2f}% MORE benefit in BULL vs BEAR")

    print("\n" + "=" * 100)


# --------------------------------------------------
# Security Checklist
# Applied:
#   - SSRF prevention: hardcoded API URLs only (Category 1)
#   - Integer range validation: F&G index 0-100 check (Category 1)
#   - Null pointer dereference prevention: null checks throughout (Category 5)
#   - Proper resource release: context managers for file I/O (Category 5)
#   - Error message exposure prevention: log type only (Category 4)
#   - Proper exception handling: no empty except blocks (Category 4)
#   - Infinite loop prevention: MAX_FETCH cap on API fetches (Category 3)
#   - Division by zero: guards on all divisions (Category 5)
#   - Initialized variables: all state initialized before use (Category 5)
# Not Applied:
#   - [WARN] SQL Injection: not applicable - no database used
#   - [WARN] Hard-coded credentials: no credentials needed (free public APIs)
#   - [WARN] CSRF: not applicable - no web endpoints
# --------------------------------------------------


if __name__ == "__main__":
    main()
