"""
Tests of the Content-Security-Policy of the interactive API docs (task019).

There is no browser here, so the policy is checked against what the page loads:
the HTML of the Swagger UI is parsed with html.parser (a parser other than the
one of the code under test) and every script, stylesheet, icon, url() of the
stylesheet and the schema URL must be of the same origin, answer 200 with the
policy of Swagger and be allowed by the directive that governs it. The rest of
the API keeps the strict policy. The expected policies are the literals of
cornflow.tests.swagger_csp_support, taken from the specification.
"""

import hashlib
import base64
import json
import unittest
from urllib.parse import urljoin, urlparse

from flask import current_app
from flask_testing import TestCase

from cornflow.commands.access import access_init_command
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.authentication import Auth
from cornflow.shared.const import PLANNER_ROLE
from cornflow.tests.const import HEALTH_URL, LOGIN_URL, USER_URL
from cornflow.tests.security_levels_support import SecurityLevelTestMixin
from cornflow.tests.swagger_csp_support import (
    BUNDLED_HTML_PAGES,
    STRICT_CSP,
    SWAGGER_CSP_WITHOUT_HASH,
    SWAGGER_DIRECTIVES,
    csp_allows,
    css_urls,
    expected_page_csp,
    parse_csp,
    parse_page,
    same_origin_path,
    schema_url,
    sha256_source,
)

CSP = "Content-Security-Policy"
STATIC_BUNDLE = "/flask-apispec/static/swagger-ui-bundle.js"
PASSWORD = "Kx9#tR2m!Qw7Zp"
SECURITY_HEADERS = (
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "Strict-Transport-Security",
    "Server",
)


class _SwaggerCspBase(SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = {}

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def ui_url(self):
        return current_app.config["APISPEC_SWAGGER_UI_URL"]

    def get_page(self):
        response = self.client.get(self.ui_url())
        self.assertEqual(200, response.status_code)
        return response, parse_page(response.get_data(as_text=True))


class _SwaggerCspCases:
    def test_page_is_html_with_the_swagger_csp(self):
        response, page = self.get_page()
        self.assertEqual("text/html", response.mimetype)
        self.assertEqual(expected_page_csp(page.inline_scripts), response.headers[CSP])
        self.assertEqual(1, len(page.inline_scripts))
        policy = parse_csp(response.headers[CSP])
        self.assertNotIn("'unsafe-inline'", policy["script-src"])
        for directive, sources in policy.items():
            self.assertNotIn("'unsafe-eval'", sources, directive)

    def test_inline_script_is_allowed_by_its_hash(self):
        response, page = self.get_page()
        sources = parse_csp(response.headers[CSP])["script-src"]
        for script in page.inline_scripts:
            self.assertIn(sha256_source(script), sources)
        hashes = [source for source in sources if source.startswith("'sha256-")]
        self.assertEqual(len(page.inline_scripts), len(hashes))

    def test_scripts_stylesheet_and_icons_are_same_origin_and_allowed(self):
        response, page = self.get_page()
        page_url = response.request.url
        policy = parse_csp(response.headers[CSP])
        self.assertTrue(page.scripts)
        self.assertTrue(page.stylesheets)
        self.assertTrue(page.icons)
        self.assertEqual([], page.other_links)
        groups = (
            ("script-src", page.scripts, ("text/javascript", "application/javascript")),
            ("style-src", page.stylesheets, ("text/css",)),
            ("img-src", page.icons, None),
            ("img-src", page.images, None),
        )
        for directive, urls, mimetypes in groups:
            for url in urls:
                with self.subTest(directive=directive, url=url):
                    path = same_origin_path(url, response)
                    self.assertIsNotNone(path, url)
                    self.assertTrue(csp_allows(policy, directive, url, page_url), url)
                    loaded = self.client.get(path)
                    self.assertEqual(200, loaded.status_code, url)
                    self.assertEqual(SWAGGER_CSP_WITHOUT_HASH, loaded.headers[CSP])
                    if mimetypes:
                        self.assertIn(loaded.mimetype, mimetypes, url)
                    else:
                        self.assertTrue(loaded.mimetype.startswith("image/"), url)

    def test_stylesheet_urls_are_data_or_same_origin(self):
        response, page = self.get_page()
        page_url = response.request.url
        policy = parse_csp(response.headers[CSP])
        self.assertTrue(page.stylesheets)
        found = 0
        for sheet in page.stylesheets:
            css = self.client.get(same_origin_path(sheet, response))
            self.assertEqual(200, css.status_code, sheet)
            for url in css_urls(css.get_data(as_text=True)):
                found += 1
                with self.subTest(sheet=sheet, url=url[:60]):
                    if not url.startswith("data:"):
                        self.assertIsNotNone(same_origin_path_of(url, page_url), url[:60])
                    self.assertTrue(csp_allows(policy, "img-src", url, page_url), url[:60])
        self.assertGreater(found, 0)

    def test_schema_url_is_same_origin_and_allowed_by_connect_src(self):
        response, page = self.get_page()
        url = schema_url(page.inline_scripts[0])
        path = same_origin_path(url, response)
        self.assertIsNotNone(path, url)
        policy = parse_csp(response.headers[CSP])
        self.assertTrue(csp_allows(policy, "connect-src", url, response.request.url))
        self.assertEqual(
            response.request.script_root + current_app.config["APISPEC_SWAGGER_URL"], url
        )
        schema = self.client.get(path)
        self.assertEqual(200, schema.status_code)
        self.assertEqual("application/json", schema.mimetype)
        self.assertTrue("swagger" in schema.json or "openapi" in schema.json)
        self.assertEqual(SWAGGER_CSP_WITHOUT_HASH, schema.headers[CSP])

    def test_swagger_csp_has_no_external_source(self):
        response, page = self.get_page()
        path = same_origin_path(schema_url(page.inline_scripts[0]), response)
        static = self.client.get(same_origin_path(page.scripts[0], response))
        for served in (response, self.client.get(path), static):
            policy = parse_csp(served.headers[CSP])
            self.assertEqual(set(SWAGGER_DIRECTIVES), set(policy))
            for directive, sources in policy.items():
                for source in sources:
                    with self.subTest(directive=directive, source=source):
                        allowed = source in ("'none'", "'self'")
                        allowed = allowed or (
                            source == "'unsafe-inline'" and directive == "style-src"
                        )
                        allowed = allowed or (source == "data:" and directive == "img-src")
                        allowed = allowed or (
                            source.startswith("'sha256-")
                            and source.endswith("'")
                            and directive == "script-src"
                        )
                        self.assertTrue(allowed, f"{directive} {source}")

    def test_rest_of_the_api_keeps_the_strict_csp(self):
        user = UserModel(
            {"username": "ana", "email": "ana@test.com", "password": PASSWORD}
        )
        user.save()
        UserRoleModel({"user_id": user.id, "role_id": PLANNER_ROLE}).save()
        token = Auth.issue_session_tokens(user)["token"]
        cases = (
            (self.client.get(HEALTH_URL), 200),
            (self.client.get("/health/"), 200),
            (
                self.client.get(
                    f"{USER_URL}{user.id}/", headers={"Authorization": f"Bearer {token}"}
                ),
                200,
            ),
            (
                self.client.post(
                    LOGIN_URL,
                    data=json.dumps({"username": "ana", "password": "wrong"}),
                    headers={"Content-Type": "application/json"},
                ),
                400,
            ),
            (self.client.get("/this-path-does-not-exist/"), 404),
        )
        for response, status in cases:
            with self.subTest(url=response.request.path):
                self.assertEqual(status, response.status_code, response.get_data())
                self.assertEqual(STRICT_CSP, response.headers[CSP])

    def test_other_security_headers_are_unchanged(self):
        response, page = self.get_page()
        reference = self.client.get("/health/")
        schema = self.client.get(
            same_origin_path(schema_url(page.inline_scripts[0]), response)
        )
        static = self.client.get(same_origin_path(page.scripts[0], response))
        for served in (response, schema, static):
            with self.subTest(url=served.request.path):
                for header in SECURITY_HEADERS:
                    self.assertEqual(
                        reference.headers.get(header), served.headers.get(header), header
                    )
                self.assertNotIn("X-Powered-By", served.headers)
        if self.security_level >= 3:
            self.assertIsNotNone(response.headers.get("Strict-Transport-Security"))
        else:
            self.assertIsNone(response.headers.get("Strict-Transport-Security"))
        self.assertEqual("no-store", response.headers["Cache-Control"])
        self.assertEqual("no-store", schema.headers["Cache-Control"])
        self.assertIn("Cache-Control", static.headers)

    def test_bundled_html_pages_get_no_script_hash(self):
        for name in BUNDLED_HTML_PAGES:
            with self.subTest(page=name):
                response = self.client.get("/flask-apispec/static/" + name)
                self.assertEqual(200, response.status_code)
                self.assertEqual(SWAGGER_CSP_WITHOUT_HASH, response.headers[CSP])

    def test_missing_static_file_is_404_with_the_swagger_csp(self):
        response = self.client.get("/flask-apispec/static/does-not-exist.js")
        self.assertEqual(404, response.status_code)
        self.assertEqual(SWAGGER_CSP_WITHOUT_HASH, response.headers[CSP])


def same_origin_path_of(url, page_url):
    """Same origin check of a URL against the URL of the page (None when foreign)."""
    page = urlparse(page_url)
    target = urlparse(urljoin(page_url, url))
    if (target.scheme, target.netloc) != (page.scheme, page.netloc):
        return None
    return target.path


class TestSwaggerCspLevel1(_SwaggerCspCases, _SwaggerCspBase):
    security_level = 1
    config_overrides = {}


class TestSwaggerCspLevel2(_SwaggerCspCases, _SwaggerCspBase):
    security_level = 2
    config_overrides = {}


class TestSwaggerCspLevel3(_SwaggerCspCases, _SwaggerCspBase):
    security_level = 3
    config_overrides = {"DOCS_ENABLED": 1}


class TestSwaggerCspApplicationRoot(_SwaggerCspCases, _SwaggerCspBase):
    security_level = 1
    config_overrides = {"APPLICATION_ROOT": "/test"}

    def test_page_urls_start_with_the_application_root(self):
        response, page = self.get_page()
        for url in (*page.scripts, *page.stylesheets, *page.icons):
            self.assertTrue(url.startswith("/test/"), url)
        self.assertTrue(schema_url(page.inline_scripts[0]).startswith("/test/"))


class TestSwaggerCspCustomUrls(_SwaggerCspCases, _SwaggerCspBase):
    security_level = 1
    config_overrides = {
        "APISPEC_SWAGGER_URL": "/api-docs/spec/",
        "APISPEC_SWAGGER_UI_URL": "/api-docs/",
    }

    def test_default_urls_are_not_served(self):
        for url in ("/swagger-ui/", "/swagger/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(404, response.status_code)
                self.assertEqual(STRICT_CSP, response.headers[CSP])


class TestSwaggerCspHashFollowsTheServedPage(_SwaggerCspBase):
    security_level = 1

    def test_hash_follows_the_url_prefix(self):
        sources = []
        for prefix in ("", "/a", "/b"):
            with self.subTest(prefix=prefix):
                kwargs = {"environ_overrides": {"SCRIPT_NAME": prefix}} if prefix else {}
                response = self.client.get("/swagger-ui/", **kwargs)
                self.assertEqual(200, response.status_code)
                page = parse_page(response.get_data(as_text=True))
                self.assertEqual(
                    expected_page_csp(page.inline_scripts), response.headers[CSP]
                )
                self.assertEqual(1, len(page.inline_scripts))
                self.assertIn(f'url: "{prefix}/swagger/"', page.inline_scripts[0])
                sources.append(sha256_source(page.inline_scripts[0]))
        self.assertEqual(3, len(set(sources)))


class TestSwaggerCspWithCustomPolicy(_SwaggerCspBase):
    security_level = 1
    config_overrides = {"CONTENT_SECURITY_POLICY": "default-src 'self'"}

    def test_custom_policy_applies_outside_the_docs_only(self):
        self.assertEqual("default-src 'self'", self.client.get(HEALTH_URL).headers[CSP])
        self.assertEqual(
            "default-src 'self'", self.client.get("/this-path-does-not-exist/").headers[CSP]
        )
        response, page = self.get_page()
        self.assertEqual(expected_page_csp(page.inline_scripts), response.headers[CSP])
        schema = self.client.get("/swagger/")
        self.assertEqual(200, schema.status_code)
        self.assertEqual(SWAGGER_CSP_WITHOUT_HASH, schema.headers[CSP])
        self.assertEqual(SWAGGER_CSP_WITHOUT_HASH, self.client.get(STATIC_BUNDLE).headers[CSP])


class _SwaggerDocsDisabledCases:
    def test_docs_routes_are_404_with_the_strict_csp(self):
        for url in ("/swagger-ui/", "/swagger/", STATIC_BUNDLE):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(404, response.status_code)
                self.assertEqual(STRICT_CSP, response.headers[CSP])


class TestSwaggerDocsDisabledLevel3(_SwaggerDocsDisabledCases, _SwaggerCspBase):
    security_level = 3
    config_overrides = {}


class TestSwaggerDocsDisabledLevel1(_SwaggerDocsDisabledCases, _SwaggerCspBase):
    security_level = 1
    config_overrides = {"DOCS_ENABLED": 0}


class TestSwaggerCspHeadersDisabled(_SwaggerCspBase):
    security_level = 1
    config_overrides = {"SECURITY_HEADERS_ENABLED": 0}

    def test_no_csp_anywhere(self):
        self.assertEqual(200, self.client.get("/swagger-ui/").status_code)
        for url in ("/swagger-ui/", "/swagger/", STATIC_BUNDLE, HEALTH_URL):
            with self.subTest(url=url):
                self.assertNotIn(CSP, self.client.get(url).headers)


def _sha(text):
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


class TestInlineScriptHashes(unittest.TestCase):
    def hashes(self, html):
        from cornflow.shared.security import inline_script_hashes

        return inline_script_hashes(html)

    def test_known_vector(self):
        self.assertEqual(
            ["'sha256-bhHHL3z2vDgxUt0W3dWQOrprscmda2Y5pLsLg4GF+pI='"],
            self.hashes("<script>alert(1)</script>"),
        )

    def test_scripts_with_src_are_skipped(self):
        html = '<script src="/a.js"></script><script type="text/javascript">x</script>'
        self.assertEqual([_sha("x")], self.hashes(html))

    def test_data_src_is_not_src(self):
        self.assertEqual([_sha("y")], self.hashes('<script data-src="a">y</script>'))

    def test_line_endings_are_normalised(self):
        self.assertEqual([_sha("a\nb\nc")], self.hashes("<script>a\r\nb\rc</script>"))

    def test_repeated_scripts_once_and_in_order(self):
        html = "<script>p</script><script>q</script><script>p</script>"
        self.assertEqual([_sha("p"), _sha("q")], self.hashes(html))

    def test_tags_are_case_insensitive(self):
        self.assertEqual([_sha("z")], self.hashes("<SCRIPT>z</SCRIPT >"))

    def test_no_inline_script(self):
        self.assertEqual([], self.hashes(""))
        self.assertEqual([], self.hashes("<p>hi</p>"))


class TestSwaggerCspValue(unittest.TestCase):
    def test_without_hashes(self):
        from cornflow.shared.security import SWAGGER_CSP, swagger_csp

        self.assertEqual(SWAGGER_CSP_WITHOUT_HASH, swagger_csp())
        self.assertEqual(SWAGGER_CSP_WITHOUT_HASH, SWAGGER_CSP)

    def test_with_hashes(self):
        from cornflow.shared.security import swagger_csp

        self.assertEqual(
            SWAGGER_CSP_WITHOUT_HASH.replace(
                "script-src 'self'", "script-src 'self' 'sha256-a' 'sha256-b'"
            ),
            swagger_csp(["'sha256-a'", "'sha256-b'"]),
        )

    def test_default_csp_is_unchanged(self):
        from cornflow.shared.security import DEFAULT_CSP

        self.assertEqual(STRICT_CSP, DEFAULT_CSP)


if __name__ == "__main__":
    unittest.main()
