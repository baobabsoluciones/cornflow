"""
Per-IP rate limiting for the sensitive unauthenticated endpoints (login,
password recovery and password reset), on top of the per-account lockout.

The account lockout protects a single account against brute force; this
rate limiter protects against spraying attacks (many usernames from one
source) and against abuse of the recovery endpoint to flood inboxes.

The limits are configurable and the whole feature can be turned off with
RATELIMIT_ENABLED=0 (it is disabled in the test configuration so the rest
of the suite, which hammers the login endpoint, is not affected).
"""

from flask import current_app, request
from flask_limiter import Limiter


def get_client_ip() -> str:
    """
    Returns the client IP used as the rate-limit key.

    When RATELIMIT_TRUST_FORWARDED_FOR is enabled (the deployment is behind a
    trusted reverse proxy that sets X-Forwarded-For), the left-most address
    of that header is used; otherwise the direct connection address is used.
    The header is only trusted when the flag is on, so clients can not spoof
    their IP on a direct deployment.

    :return: the client IP address
    :rtype: str
    """
    try:
        trust_forwarded = int(
            current_app.config.get("RATELIMIT_TRUST_FORWARDED_FOR", 0)
        )
    except (TypeError, ValueError):
        trust_forwarded = 0

    if trust_forwarded:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


# Module-level singleton, initialised in app.py through init_app (same
# pattern as db and bcrypt). Default limits are empty: only the decorated
# endpoints are limited.
limiter = Limiter(key_func=get_client_ip)

# Message returned (as flask-restful "message") when a limit is exceeded
RATE_LIMIT_MESSAGE = "Too many requests. Please slow down and try again later."


def login_rate_limit() -> str:
    """Rate limit string for the login endpoint (per IP)."""
    return current_app.config.get("RATELIMIT_LOGIN", "10 per minute")


def recover_rate_limit() -> str:
    """Rate limit string for the password recovery / reset endpoints (per IP)."""
    return current_app.config.get("RATELIMIT_RECOVER", "5 per hour")
