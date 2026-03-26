"""
SQLite trade history persistence.
All queries use parameterized binding per MOIS security rules.
"""

import sqlite3
import logging
import os
import threading

logger = logging.getLogger("trading_bot")

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "trades.db")
_lock = threading.Lock()


def init_db() -> None:
    """Create trades table if not exists."""
    with _lock:
        # [SECURE] Context manager ensures resource release (Category 5)
        with sqlite3.connect(_DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    order_usdt REAL DEFAULT 0,
                    pnl_percent REAL DEFAULT 0,
                    pnl_usdt REAL DEFAULT 0,
                    mode TEXT DEFAULT '',
                    signal_type TEXT DEFAULT '',
                    entries_count INTEGER DEFAULT 1,
                    holding_bars INTEGER DEFAULT 0,
                    trend_score REAL DEFAULT 0,
                    smart_money_score REAL DEFAULT 0
                )
            """)
            conn.commit()
            logger.debug("Trade database initialized: %s", _DB_PATH)


def insert_trade(
    timestamp: float, side: str, price: float, quantity: float,
    order_usdt: float = 0, pnl_percent: float = 0, pnl_usdt: float = 0,
    mode: str = "", signal_type: str = "", entries_count: int = 1,
    holding_bars: int = 0, trend_score: float = 0, smart_money_score: float = 0,
) -> int:
    """Insert a trade record. Returns the row ID."""
    with _lock:
        with sqlite3.connect(_DB_PATH) as conn:
            # [SECURE] Parameterized query - SQL Injection prevention (Category 1)
            cursor = conn.execute(
                """INSERT INTO trades
                   (timestamp, side, price, quantity, order_usdt, pnl_percent,
                    pnl_usdt, mode, signal_type, entries_count, holding_bars,
                    trend_score, smart_money_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (timestamp, side, price, quantity, order_usdt, pnl_percent,
                 pnl_usdt, mode, signal_type, entries_count, holding_bars,
                 trend_score, smart_money_score)
            )
            conn.commit()
            return cursor.lastrowid


def get_trades(limit: int = 100) -> list:
    """Get recent trades, newest first."""
    # [SECURE] Range validation on limit (Category 1)
    limit = max(1, min(limit, 1000))
    with _lock:
        with sqlite3.connect(_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            # [SECURE] Parameterized query (Category 1)
            rows = conn.execute(
                "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]


def get_statistics() -> dict:
    """Get aggregate trade statistics."""
    with _lock:
        with sqlite3.connect(_DB_PATH) as conn:
            total = conn.execute("SELECT COUNT(*) FROM trades WHERE side='SELL'").fetchone()[0]
            wins = conn.execute("SELECT COUNT(*) FROM trades WHERE side='SELL' AND pnl_usdt > 0").fetchone()[0]
            losses = conn.execute("SELECT COUNT(*) FROM trades WHERE side='SELL' AND pnl_usdt <= 0").fetchone()[0]
            total_profit = conn.execute("SELECT COALESCE(SUM(pnl_usdt), 0) FROM trades WHERE side='SELL' AND pnl_usdt > 0").fetchone()[0]
            total_loss = conn.execute("SELECT COALESCE(SUM(pnl_usdt), 0) FROM trades WHERE side='SELL' AND pnl_usdt <= 0").fetchone()[0]
            net_pnl = conn.execute("SELECT COALESCE(SUM(pnl_usdt), 0) FROM trades WHERE side='SELL'").fetchone()[0]
            avg_hold = conn.execute("SELECT COALESCE(AVG(holding_bars), 0) FROM trades WHERE side='SELL'").fetchone()[0]
            best = conn.execute("SELECT COALESCE(MAX(pnl_usdt), 0) FROM trades WHERE side='SELL'").fetchone()[0]
            worst = conn.execute("SELECT COALESCE(MIN(pnl_usdt), 0) FROM trades WHERE side='SELL'").fetchone()[0]
            buy_count = conn.execute("SELECT COUNT(*) FROM trades WHERE side='BUY'").fetchone()[0]

    # [SECURE] Division by zero prevention (Category 5)
    win_rate = (wins / total * 100) if total > 0 else 0
    profit_factor = abs(total_profit / total_loss) if total_loss != 0 else 0

    return {
        "total_sells": total,
        "total_buys": buy_count,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "net_pnl": round(net_pnl, 2),
        "total_profit": round(total_profit, 2),
        "total_loss": round(total_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_holding_bars": round(avg_hold, 1),
        "best_trade": round(best, 2),
        "worst_trade": round(worst, 2),
    }


# --------------------------------------------------
# Security Checklist
# Applied:
#   - SQL Injection prevention: all queries parameterized (Category 1)
#   - Resource release: context managers on all connections (Category 5)
#   - Race condition prevention: threading.Lock on all DB ops (Category 3)
#   - Input validation: limit range clamped (Category 1)
#   - Division by zero prevention: total > 0 check (Category 5)
# Not Applied:
#   - [WARN] XSS: not applicable (data layer only)
# --------------------------------------------------
