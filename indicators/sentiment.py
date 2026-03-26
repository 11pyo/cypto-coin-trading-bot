"""
Fear and Greed Index fetcher from alternative.me API.
Cached with 1-hour TTL to avoid excessive API calls.
"""

import time
import logging
import requests

logger = logging.getLogger("trading_bot")

# [SECURE] Hardcoded URL constant - prevents SSRF (Category 1)
FEAR_GREED_API_URL = "https://api.alternative.me/fng/?limit=1&format=json"

# Module-level cache
_cached_value = None
_cached_timestamp = 0.0
_CACHE_TTL_SECONDS = 3600  # 1 hour


def fetch_fear_greed_index() -> int | None:
    """Fetch the current Crypto Fear and Greed Index.

    Returns:
        Integer value 0-100 (0=Extreme Fear, 100=Extreme Greed),
        or None if the API call fails.
    """
    global _cached_value, _cached_timestamp

    # Return cached value if still valid
    if _cached_value is not None and (time.time() - _cached_timestamp) < _CACHE_TTL_SECONDS:
        return _cached_value

    try:
        # [SECURE] Fixed URL - no user input in URL construction (SSRF prevention, Category 1)
        response = requests.get(FEAR_GREED_API_URL, timeout=10)
        response.raise_for_status()

        data = response.json()

        # [SECURE] Null check on response structure (Category 5)
        if data is None or "data" not in data or not data["data"]:
            logger.warning("Fear/Greed API returned unexpected format")
            return None

        value = int(data["data"][0]["value"])

        # [SECURE] Range validation - integer overflow prevention (Category 1)
        if not 0 <= value <= 100:
            logger.warning("Fear/Greed index out of expected range: %d", value)
            return None

        _cached_value = value
        _cached_timestamp = time.time()
        logger.debug("Fear/Greed Index: %d (%s)", value, data["data"][0].get("value_classification", ""))
        return value

    except requests.RequestException as e:
        # [SECURE] Log error without exposing internal details to user (Category 4)
        logger.warning("Failed to fetch Fear/Greed index: %s", type(e).__name__)
        return None
    except (ValueError, KeyError, IndexError) as e:
        # [SECURE] Handle malformed response - no empty except (Category 4)
        logger.warning("Failed to parse Fear/Greed response: %s", type(e).__name__)
        return None


# --------------------------------------------------
# Security Checklist
# Applied:
#   - SSRF prevention: hardcoded API URL, no user input in URL (Category 1)
#   - Integer range validation: check 0-100 range (Category 1)
#   - Null pointer dereference prevention: validate response structure (Category 5)
#   - Error message info exposure prevention: log type only, not details (Category 4)
#   - Proper exception handling: no empty except blocks (Category 4)
# Not Applied:
#   - [WARN] SQL Injection: not applicable - no database used
# --------------------------------------------------
