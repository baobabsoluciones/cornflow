"""
HTTP security response headers and CORS configuration.

These headers are instructions to *browsers* (the cornflow-ui SPA and the
optional Swagger docs page). Non-browser clients — cornflow-client, Airflow
and the CLI — ignore them, so the machine-to-machine paths are unaffected.

A single ``after_request`` hook stamps the headers on every response
(including error responses). Everything is driven by config so a deployment
can tune or disable it. The Content-Security-Policy depends on the route:

- the responses of the interactive API docs (the ``flask-apispec`` blueprint:
  the Swagger UI page, its static files and the OpenAPI schema, registered
  only with DOCS_ENABLED) get SWAGGER_CSP, which lets the Swagger UI load
  from this origin and allows the inline script of the page by its hash;
- every other response gets CONTENT_SECURITY_POLICY or, when it is not set,
  the deny-by-default DEFAULT_CSP, because the API serves only JSON.

CONTENT_SECURITY_POLICY does not change the policy of the docs.
"""

import base64
import hashlib
import re

from flask import current_app, request

# Deny-by-default Content-Security-Policy of every response but the interactive
# API docs: the API returns JSON, so nothing needs to load resources.
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


# Blueprint that flask-apispec registers for the interactive API docs (only
# with DOCS_ENABLED): the Swagger UI page, its static files and the schema.
SWAGGER_BLUEPRINT = "flask-apispec"
SWAGGER_UI_ENDPOINT = SWAGGER_BLUEPRINT + ".swagger-ui"

# Content-Security-Policy of the interactive API docs. The Swagger UI is served
# from the static files bundled with flask-apispec (no CDN), so only this
# origin is allowed.
SWAGGER_CSP_DIRECTIVES = (
    # Nothing else may load: fonts, frames, objects, media, workers...
    "default-src 'none'",
    # The bundled swagger-ui scripts. The inline script that starts the page
    # is allowed by its sha256 hash, added to the page response. Neither
    # 'unsafe-inline' nor 'unsafe-eval': the bundle does not evaluate code
    # when it loads or runs "Try it out".
    "script-src 'self'",
    # The bundled stylesheet. 'unsafe-inline' because swagger-ui sets style
    # attributes (syntax highlighting of examples and responses, alignment of
    # markdown tables); styles can not run code.
    "style-src 'self' 'unsafe-inline'",
    # The favicons and the data: images embedded in swagger-ui.css.
    "img-src 'self' data:",
    # fetch of the OpenAPI schema and the "Try it out" requests (same origin).
    "connect-src 'self'",
    # As DEFAULT_CSP: no framing and no <base> element.
    "frame-ancestors 'none'",
    "base-uri 'none'",
)

_INLINE_SCRIPT_RE = re.compile(
    r"<script\b(?P<attrs>[^>]*)>(?P<body>.*?)</script\s*>", re.IGNORECASE | re.DOTALL
)
_SRC_ATTRIBUTE_RE = re.compile(r"(?:^|\s)src\s*=", re.IGNORECASE)


def swagger_csp(script_hashes=()) -> str:
    """
    Content-Security-Policy of the interactive API docs.

    :param script_hashes: CSP source expressions (``'sha256-...'``) of the
                          inline scripts to allow, added to script-src
    :return: the header value
    """
    directives = []
    for directive in SWAGGER_CSP_DIRECTIVES:
        if directive.startswith("script-src ") and script_hashes:
            directive = " ".join([directive, *script_hashes])
        directives.append(directive)
    return "; ".join(directives)


# Policy of the static files and the schema of the docs (no inline script)
SWAGGER_CSP = swagger_csp()


def inline_script_hashes(html: str) -> list:
    """
    CSP hash sources (``'sha256-<base64>'``) of the inline scripts of an HTML
    page, in order and without repetitions. Scripts with a ``src`` attribute
    are skipped. Line endings are normalised to LF, as the HTML parser of the
    browser does before hashing the script text.

    :param html: the HTML text as served
    :return: list of CSP source expressions
    """
    sources = []
    for match in _INLINE_SCRIPT_RE.finditer(html):
        if _SRC_ATTRIBUTE_RE.search(match.group("attrs")):
            continue
        body = match.group("body").replace("\r\n", "\n").replace("\r", "\n")
        digest = hashlib.sha256(body.encode("utf-8")).digest()
        source = "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"
        if source not in sources:
            sources.append(source)
    return sources


def _served_inline_script_hashes(response) -> list:
    """
    Hashes of the inline scripts of the Swagger UI page as served. An empty
    list (the inline script will not run) when the body can not be read as
    text: not HTML, streamed, passthrough or already encoded.
    """
    if (
        response.mimetype != "text/html"
        or response.direct_passthrough
        or response.is_streamed
        or response.headers.get("Content-Encoding")
    ):
        return []
    return inline_script_hashes(response.get_data(as_text=True))


def _content_security_policy(app, response) -> str:
    """Content-Security-Policy of the response, according to its route."""
    if request.blueprint == SWAGGER_BLUEPRINT:
        hashes = ()
        if request.endpoint == SWAGGER_UI_ENDPOINT:
            hashes = _served_inline_script_hashes(response)
        return swagger_csp(hashes)
    return app.config.get("CONTENT_SECURITY_POLICY") or DEFAULT_CSP


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
    headers["Content-Security-Policy"] = _content_security_policy(app, response)
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
