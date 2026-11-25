"""
Per-IP rate limiting for the sensitive unauthenticated endpoints (login,
token refresh, logout, password recovery and password reset), on top of the
per-account lockout.

The account lockout protects a single account against brute force; this
rate limiter protects against spraying attacks (many usernames from one
source) and against abuse of the recovery endpoint to flood inboxes.

In login, token refresh and logout only the failed responses (status 400 or
above) count, so successful logins (also those of Airflow tasks, which log in
many times in a row) do not use up the limit. In recovery and reset every
request counts, because the recovery always answers 200 so as not to reveal
which accounts exist.

The limits are configurable and the whole feature can be turned off with
RATELIMIT_ENABLED=0 (it is disabled in the test configuration so the rest
of the suite, which hammers the login endpoint, is not affected).
"""

from flask import Response, current_app, request
from flask_limiter import Limiter
from flask_limiter.extension import LimitDecorator

from cornflow.shared.const import FAILED_RESPONSE_MIN_STATUS


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


def is_failed_response(response: Response) -> bool:
    """
    Tells whether a response counts as a failed attempt for the limits that
    only count failures: any status code of 400 or above (wrong credentials,
    invalid or revoked tokens, locked accounts, malformed requests, server
    errors and the 429 answered when the limit is already exceeded).

    Successful responses (2xx), including the intermediate login step that
    asks for the second factor or for the MFA enrollment, do not count.

    :param response: the response returned to the client
    :return: True if the response must consume the rate limit
    :rtype: bool
    """
    return response.status_code >= FAILED_RESPONSE_MIN_STATUS


def login_rate_limit() -> str:
    """Rate limit string for the login endpoint (per IP)."""
    return current_app.config.get("RATELIMIT_LOGIN", "10 per minute")


def recover_rate_limit() -> str:
    """Rate limit string for the password recovery / reset endpoints (per IP)."""
    return current_app.config.get("RATELIMIT_RECOVER", "5 per hour")


def failed_attempts_limit(scope: str) -> LimitDecorator:
    """
    Per-IP limit (RATELIMIT_LOGIN) that only consumes on failed responses,
    for the endpoints that take a credential in the body: login, token
    refresh and logout.

    The limit is checked before the request runs (a client that has used up
    its failures gets a 429 even with valid credentials) and consumed after
    it, only when the response is a failure (is_failed_response). Each scope
    keeps its own counter per client IP.

    The check and the deduction are not atomic: requests from the same IP
    that are being processed at the same time are all checked before any of
    them is counted, so a burst of parallel failures can go slightly over the
    limit. The per-account lockout (LOGIN_MAX_ATTEMPTS) still applies.

    :param scope: name of the shared counter (e.g. "login")
    :return: the decorator to put in the endpoint ``decorators`` list
    """
    return limiter.shared_limit(
        login_rate_limit,
        scope=scope,
        error_message=RATE_LIMIT_MESSAGE,
        deduct_when=is_failed_response,
    )
