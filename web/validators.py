"""
Settings input validation - whitelist, type checking, range validation.
"""

# [SECURE] Whitelist of modifiable settings with type and range (Category 1)
SETTING_RULES = {
    "rsi_buy_threshold":        {"type": float, "min": 10.0, "max": 50.0},
    "rsi_sell_threshold":       {"type": float, "min": 50.0, "max": 95.0},
    "bb_buy_multiplier":        {"type": float, "min": 0.90, "max": 1.10},
    "bb_sell_multiplier":       {"type": float, "min": 0.90, "max": 1.10},
    "fg_buy_threshold":         {"type": float, "min": 5.0,  "max": 50.0},
    "fg_sell_threshold":        {"type": float, "min": 50.0, "max": 95.0},
    "max_position_percent":     {"type": float, "min": 0.05, "max": 0.80},
    "stop_loss_percent":        {"type": float, "min": 0.02, "max": 0.30},
    "take_profit_percent":      {"type": float, "min": 0.03, "max": 0.50},
    "min_order_size_usdt":      {"type": float, "min": 5.0,  "max": 100.0},
    "dca_enabled":              {"type": bool},
    "dca_max_entries":          {"type": int,   "min": 1,    "max": 10},
    "dca_drop_percent_1":       {"type": float, "min": 0.02, "max": 0.20},
    "dca_drop_percent_2":       {"type": float, "min": 0.03, "max": 0.30},
    "dca_drop_percent_3":       {"type": float, "min": 0.05, "max": 0.40},
    "dca_multiplier_1":         {"type": float, "min": 1.0,  "max": 5.0},
    "dca_multiplier_2":         {"type": float, "min": 1.0,  "max": 5.0},
    "dca_multiplier_3":         {"type": float, "min": 1.0,  "max": 5.0},
    "dca_max_total_percent":    {"type": float, "min": 0.10, "max": 0.90},
    "dca_require_signal":       {"type": bool},
    "trend_threshold":          {"type": float, "min": 20.0, "max": 80.0},
    "trend_position_multiplier":{"type": float, "min": 1.0,  "max": 10.0},
    "trend_trailing_stop_pct":  {"type": float, "min": 0.02, "max": 0.15},
    "trend_min_hold_bars":      {"type": int,   "min": 1,    "max": 48},
    "range_min_hold_bars":      {"type": int,   "min": 1,    "max": 24},
    "trading_interval_seconds": {"type": int,   "min": 60,   "max": 3600},
}


def validate_setting(key: str, value) -> tuple[bool, str, any]:
    """Validate a single setting key/value pair.

    Returns:
        (is_valid, error_message, sanitized_value)
    """
    # [SECURE] Whitelist check (Category 1)
    if key not in SETTING_RULES:
        return False, f"Unknown setting: {key}", None

    rule = SETTING_RULES[key]
    expected_type = rule["type"]

    # Type coercion
    try:
        if expected_type == bool:
            if isinstance(value, str):
                sanitized = value.lower() in ("true", "1", "yes", "on")
            else:
                sanitized = bool(value)
        elif expected_type == int:
            sanitized = int(float(value))
        elif expected_type == float:
            sanitized = float(value)
        else:
            return False, f"Unsupported type for {key}", None
    except (ValueError, TypeError):
        return False, f"Invalid value for {key}: {value}", None

    # Range check
    if "min" in rule and sanitized < rule["min"]:
        return False, f"{key} must be >= {rule['min']}", None
    if "max" in rule and sanitized > rule["max"]:
        return False, f"{key} must be <= {rule['max']}", None

    return True, "", sanitized


def validate_settings(data: dict) -> tuple[dict, list]:
    """Validate multiple settings. Returns (valid_settings, errors)."""
    valid = {}
    errors = []
    for key, value in data.items():
        ok, err, sanitized = validate_setting(key, value)
        if ok:
            valid[key] = sanitized
        else:
            errors.append(err)
    return valid, errors


# --------------------------------------------------
# Security Checklist
# Applied:
#   - Input validation whitelist: only allowed keys accepted (Category 1)
#   - Type coercion with error handling: prevents type confusion (Category 1)
#   - Range validation: prevents extreme values (Category 1)
# Not Applied:
#   - [WARN] SQL Injection: not applicable (no DB here)
# --------------------------------------------------
