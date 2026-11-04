"""
In-memory sliding window rate limiter for security-sensitive API endpoints.
Provides defense against credential stuffing and order flooding without external dependencies.
"""
import time
import threading
from collections import defaultdict
from functools import wraps
from flask import request, jsonify, current_app


class InMemoryRateLimiter:
    """Thread-safe sliding window rate limiter using in-memory timestamps."""

    def __init__(self):
        self._records: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def get_client_ip(self) -> str:
        """Extract client IP, taking first IP from X-Forwarded-For if behind a proxy."""
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()
            if client_ip:
                return client_ip
        return request.remote_addr or "127.0.0.1"

    def is_allowed(self, key: str, limit: int, period: int) -> tuple[bool, int]:
        """
        Check if request is allowed under sliding window.
        Returns: (allowed: bool, retry_after: int)
        """
        now = time.monotonic()
        cutoff = now - period

        with self._lock:
            timestamps = self._records[key]
            # Retain only timestamps within the sliding window
            valid_timestamps = [t for t in timestamps if t > cutoff]
            self._records[key] = valid_timestamps

            if len(valid_timestamps) >= limit:
                oldest = valid_timestamps[0]
                retry_after = max(1, int(period - (now - oldest)) + 1)
                return False, retry_after

            valid_timestamps.append(now)
            return True, 0

    def reset(self):
        """Clear all rate limit records. Essential for test isolation."""
        with self._lock:
            self._records.clear()


# Global singleton instance
limiter = InMemoryRateLimiter()


def rate_limit(key_prefix: str, default_limit: int = 10, default_period: int = 60):
    """
    Flask route decorator that enforces rate limits per client IP.
    Respects app.config['RATELIMIT_ENABLED'].
    Dynamically loads limit/period overrides from app.config if configured.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_app.config.get("RATELIMIT_ENABLED", True):
                return f(*args, **kwargs)

            # Check config overrides
            config_limit_key = f"RATELIMIT_{key_prefix.upper()}_LIMIT"
            config_period_key = f"RATELIMIT_{key_prefix.upper()}_PERIOD"

            limit = current_app.config.get(config_limit_key, default_limit)
            period = current_app.config.get(config_period_key, default_period)

            client_ip = limiter.get_client_ip()
            key = f"{key_prefix}:{client_ip}"

            allowed, retry_after = limiter.is_allowed(key, limit=limit, period=period)
            if not allowed:
                response = jsonify({
                    "error": f"Too many requests. Limit of {limit} requests per {period}s exceeded.",
                    "retry_after": retry_after,
                })
                response.status_code = 429
                response.headers["Retry-After"] = str(retry_after)
                return response

            return f(*args, **kwargs)
        return decorated_function
    return decorator
