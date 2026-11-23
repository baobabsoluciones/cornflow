"""
Helpers to check the Content-Security-Policy of the interactive API docs
(Swagger UI) against what the page loads.

Kept outside tests/unit so that unittest discovery does not collect it. The
expected policies are written here as literals, taken from the specification:
they are not imported from cornflow.shared.security.
"""

import base64
import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

STRICT_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
SWAGGER_CSP_WITHOUT_HASH = (
    "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
)
SWAGGER_DIRECTIVES = (
    "default-src",
    "script-src",
    "style-src",
    "img-src",
    "connect-src",
    "frame-ancestors",
    "base-uri",
)
# Static files of swagger-ui-dist served by the flask-apispec blueprint
BUNDLED_HTML_PAGES = ("index.html", "oauth2-redirect.html")


class SwaggerPage(HTMLParser):
    """Resources that an HTML page loads, as the parser of a browser sees them."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.scripts = []
        self.inline_scripts = []
        self.stylesheets = []
        self.icons = []
        self.images = []
        self.other_links = []
        self._inline = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            if attrs.get("src") is not None:
                self.scripts.append(attrs["src"])
            else:
                self._inline = []
        elif tag == "link" and attrs.get("href") is not None:
            rel = (attrs.get("rel") or "").lower().split()
            if "stylesheet" in rel:
                self.stylesheets.append(attrs["href"])
            elif any("icon" in token for token in rel):
                self.icons.append(attrs["href"])
            else:
                self.other_links.append(attrs["href"])
        elif tag == "img" and attrs.get("src") is not None:
            self.images.append(attrs["src"])

    def handle_data(self, data):
        if self._inline is not None:
            self._inline.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._inline is not None:
            self.inline_scripts.append("".join(self._inline))
            self._inline = None


def parse_page(html) -> SwaggerPage:
    page = SwaggerPage()
    page.feed(html)
    page.close()
    return page


def sha256_source(text) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"


def parse_csp(value) -> dict:
    """directive -> list of sources. Fails if a directive is repeated."""
    directives = {}
    for part in value.split(";"):
        tokens = part.split()
        if not tokens:
            continue
        name, sources = tokens[0], tokens[1:]
        assert name not in directives, f"repeated directive {name} in {value!r}"
        directives[name] = sources
    return directives


def expected_page_csp(inline_scripts) -> str:
    """The CSP of the Swagger UI page: the one without hash plus one hash per inline script."""
    sources = []
    for script in inline_scripts:
        source = sha256_source(script)
        if source not in sources:
            sources.append(source)
    old = "script-src 'self'"
    new = " ".join([old, *sources])
    assert old in SWAGGER_CSP_WITHOUT_HASH
    return SWAGGER_CSP_WITHOUT_HASH.replace(old, new, 1)


def schema_url(inline_script) -> str:
    return re.search(r'\burl:\s*"([^"]*)"', inline_script).group(1)


def css_urls(css_text) -> list:
    return [value for _, value in re.findall(r"url\(\s*(['\"]?)(.*?)\1\s*\)", css_text)]


def same_origin_path(url, response):
    """
    Path (without the script root, ready for the test client) of a URL of the
    page when it is of the same origin as the page; None otherwise.
    """
    page_url = response.request.url
    page = urlparse(page_url)
    target = urlparse(urljoin(page_url, url))
    if (target.scheme, target.netloc) != (page.scheme, page.netloc):
        return None
    path = target.path
    root = response.request.script_root
    if root and path.startswith(root):
        path = path[len(root):]
    if target.query:
        path += "?" + target.query
    return path


def csp_allows(policy, directive, url, page_url) -> bool:
    """Whether the policy (string or parsed) lets the page load the URL with the directive."""
    if isinstance(policy, str):
        policy = parse_csp(policy)
    sources = policy.get(directive, policy.get("default-src", []))
    if url.startswith("data:"):
        return "data:" in sources
    page = urlparse(page_url)
    target = urlparse(urljoin(page_url, url))
    if (target.scheme, target.netloc) == (page.scheme, page.netloc):
        return "'self'" in sources
    return False
