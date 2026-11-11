"""
HTTP security response headers and CORS configuration.

These headers are instructions to *browsers* (the cornflow-ui SPA and the
optional Swagger docs page). Non-browser clients — cornflow-client, Airflow
and the CLI — ignore them, so the machine-to-machine paths are unaffected.

A single ``after_request`` hook stamps the headers on every response
(including error responses). Everything is driven by config so a deployment
can tune or disable it; the defaults are strict because in production the API
serves only JSON and the interactive docs are disabled.
"""

from flask import current_app

# Deny-by-default Content-Security-Policy. The API returns JSON and, in
# production, the Swagger UI is off, so nothing needs to load resources.
DEFAULT_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"

# Do not leak the URL (which may carry tokens, e.g. the password reset link)
# through the Referer header.
DEFAULT_REFERRER_POLICY = "no-referrer"

# Switch off browser features the application does not use.
DEFAULT_PERMISSIONS_POLICY = (
    "accelerometer=(), autoplay=(), camera=(), display-capture=(), "
    "encrypted-media=(), fullscreen=(), geolocation=(), gyroscope=(), "
    "magnetometer=(), microphone=(), midi=(), payment=(), usb=()"
)


def _hsts_value(app):
    """Builds the Strict-Transport-Security header value from config."""
    parts = [f"max-age={int(app.config.get('HSTS_MAX_AGE', 31536000))}"]
    if int(app.config.get("HSTS_INCLUDE_SUBDOMAINS", 1)):
        parts.append("includeSubDomains")
    if int(app.config.get("HSTS_PRELOAD", 0)):
        parts.append("preload")
    return "; ".join(parts)


def _apply_security_headers(response):
    """after_request hook that adds the security headers to a response."""
    app = current_app
    if not int(app.config.get("SECURITY_HEADERS_ENABLED", 1)):
        return response

    headers = response.headers
    headers["X-Content-Type-Options"] = "nosniff"
    headers["X-Frame-Options"] = "DENY"
    headers["Content-Security-Policy"] = (
        app.config.get("CONTENT_SECURITY_POLICY") or DEFAULT_CSP
    )
    headers["Referrer-Policy"] = (
        app.config.get("REFERRER_POLICY") or DEFAULT_REFERRER_POLICY
    )
    headers["Permissions-Policy"] = (
        app.config.get("PERMISSIONS_POLICY") or DEFAULT_PERMISSIONS_POLICY
    )

    # Responses carry authentication data, so ask browsers and proxies not to
    # cache them (unless a view has already set its own caching policy).
    if int(app.config.get("SECURITY_NO_STORE", 1)) and "Cache-Control" not in headers:
        headers["Cache-Control"] = "no-store"

    # HSTS is only meaningful behind TLS; gated by its own flag because a
    # browser that has seen it will refuse plain HTTP afterwards.
    if int(app.config.get("HSTS_ENABLED", 0)):
        headers["Strict-Transport-Security"] = _hsts_value(app)

    # Reduce version fingerprinting: overwrite the server banner and drop the
    # X-Powered-By header if some layer added it.
    headers["Server"] = app.config.get("SERVICE_NAME", "Cornflow")
    headers.pop("X-Powered-By", None)

    return response


def init_security_headers(app):
    """Registers the security-headers ``after_request`` hook on the app."""
    app.after_request(_apply_security_headers)


def resolve_cors_origins(raw):
    """
    Normalises the CORS_ORIGINS config value into what flask-cors expects.

    - ``"*"`` (the development default) allows any origin.
    - an empty value (the production default) allows none (default-closed).
    - a comma-separated string becomes an explicit allow-list.

    :param raw: the CORS_ORIGINS config value
    :return: ``"*"`` or a (possibly empty) list of allowed origins
    """
    if isinstance(raw, (list, tuple)):
        origins = [str(o).strip() for o in raw if str(o).strip()]
        return "*" if origins == ["*"] else origins
    if raw is None:
        return []
    raw = str(raw).strip()
    if raw == "*":
        return "*"
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
