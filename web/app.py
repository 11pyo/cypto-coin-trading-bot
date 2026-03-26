"""
Flask web application for the trading bot dashboard.
"""

import os
import logging
import secrets as sec
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

from web.validators import validate_settings
from config.defaults import OPTIMIZED_DEFAULTS
from state import trade_db

logger = logging.getLogger("trading_bot")


def create_app(bot_state):
    """Create Flask app with SocketIO.

    Args:
        bot_state: BotState instance shared with trading loop.

    Returns:
        Tuple of (Flask app, SocketIO instance).
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    # [SECURE] Secret key from env or generated (Category 2)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", sec.token_hex(32))

    socketio = SocketIO(app, async_mode="gevent", cors_allowed_origins=[])

    # --- Routes ---

    @app.route("/")
    def dashboard():
        """Serve the main dashboard page."""
        return render_template("dashboard.html")

    @app.route("/api/state")
    def api_state():
        """Get current bot state snapshot."""
        return jsonify(bot_state.get_snapshot())

    @app.route("/api/trades")
    def api_trades():
        """Get trade history."""
        # [SECURE] Input validation on query param (Category 1)
        try:
            limit = int(request.args.get("limit", 100))
            limit = max(1, min(limit, 500))
        except (ValueError, TypeError):
            limit = 100
        trades = trade_db.get_trades(limit)
        return jsonify(trades)

    @app.route("/api/statistics")
    def api_statistics():
        """Get trade statistics."""
        stats = trade_db.get_statistics()
        return jsonify(stats)

    @app.route("/api/settings", methods=["POST"])
    def api_settings():
        """Update bot settings."""
        # [SECURE] Validate all input (Category 1)
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid request"}), 400

        valid, errors = validate_settings(data)
        if errors:
            return jsonify({"error": errors}), 400

        for key, value in valid.items():
            bot_state.update_setting(key, value)

        return jsonify({"ok": True, "updated": list(valid.keys())})

    @app.route("/api/settings/reset", methods=["POST"])
    def api_reset_settings():
        """Reset settings to optimized defaults."""
        bot_state.reset_settings(OPTIMIZED_DEFAULTS)
        return jsonify({"ok": True, "settings": OPTIMIZED_DEFAULTS})

    @app.route("/api/toggle", methods=["POST"])
    def api_toggle():
        """Toggle auto-trading on/off."""
        bot_state.auto_trading_enabled = not bot_state.auto_trading_enabled
        state = "ON" if bot_state.auto_trading_enabled else "OFF"
        logger.info("Auto-trading toggled: %s", state)
        return jsonify({"auto_trading": bot_state.auto_trading_enabled})

    # --- SocketIO ---

    @socketio.on("connect")
    def handle_connect():
        """Send current state on client connect."""
        socketio.emit("cycle_update", bot_state.get_snapshot())

    # --- Error handlers ---

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        # [SECURE] Generic error to client (Category 4)
        logger.error("Server error: %s", e)
        return jsonify({"error": "Internal error"}), 500

    return app, socketio


# --------------------------------------------------
# Security Checklist
# Applied:
#   - Hard-coded credentials prevention: SECRET_KEY from env or random (Category 2)
#   - Input validation: all POST data validated via validators.py (Category 1)
#   - Error message exposure prevention: generic 500 response (Category 4)
#   - CORS: empty allowed_origins blocks cross-origin (Category 1)
#   - XSS: Jinja2 auto-escapes by default
# Not Applied:
#   - [WARN] CSRF: consider adding Flask-WTF for production deployment
# --------------------------------------------------
