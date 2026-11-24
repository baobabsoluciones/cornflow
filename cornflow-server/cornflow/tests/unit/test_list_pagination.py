"""
Tests for the pagination headers of the list endpoints: the body is still a
bare JSON list of at most ``limit`` rows, and the headers tell the client how
many rows exist.
"""

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from flask import current_app
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.models import CaseModel, ExecutionModel, InstanceModel
from cornflow.shared import db
from cornflow.shared.const import ADMIN_ROLE, PLANNER_ROLE, PLATFORM_PLANNER_ROLE
from cornflow.tests.const import (
    CASE_PATH,
    CASE_URL,
    EXECUTION_PATH,
    EXECUTION_URL,
    EXECUTION_URL_NORUN,
    INSTANCE_PATH,
    INSTANCE_URL,
)
from cornflow.tests.custom_test_case import CustomTestCase
from cornflow.tests.unit.test_platform_isolation import _RoleUserMixin, auth_header

ROWS = 12


def total(response):
    return int(response.headers["X-Total-Count"])


class TestListTotalCount(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.instance_payload = self.load_file(INSTANCE_PATH)
        self.instance_ids = [
            self.create_new_row(INSTANCE_URL, InstanceModel, self.instance_payload)
            for _ in range(ROWS)
        ]
        execution_payload = self.load_file(EXECUTION_PATH)
        execution_payload["instance_id"] = self.instance_ids[0]
        for _ in range(ROWS):
            self.create_new_row(EXECUTION_URL_NORUN, ExecutionModel, execution_payload)
        self.case_payload = self.load_file(CASE_PATH)

    def get(self, url, token=None, **params):
        return self.client.get(
            url,
            query_string=params,
            headers=self.get_header_with_auth(token or self.token),
        )

    def test_total_counts_every_visible_row_while_body_is_one_page(self):
        for url in (INSTANCE_URL, EXECUTION_URL):
            with self.subTest(url=url):
                response = self.get(url)
                self.assertEqual(200, response.status_code)
                self.assertEqual(10, len(response.json))
                self.assertEqual(ROWS, total(response))

    def test_total_does_not_depend_on_offset_and_limit(self):
        for url in (INSTANCE_URL, EXECUTION_URL):
            with self.subTest(url=url):
                last_page = self.get(url, offset=10)
                self.assertEqual(2, len(last_page.json))
                self.assertEqual(ROWS, total(last_page))
                self.assertEqual("10", last_page.headers["X-Offset"])

                small_page = self.get(url, limit=5)
                self.assertEqual(5, len(small_page.json))
                self.assertEqual(ROWS, total(small_page))
                self.assertEqual("5", small_page.headers["X-Limit"])

    def test_link_header_points_to_the_neighbour_pages(self):
        response = self.get(EXECUTION_URL, limit=5, offset=5, schema="solve_model_dag")
        links = {}
        for part in response.headers["Link"].split(", "):
            target, rel = part.split("; ")
            links[rel] = parse_qs(urlparse(target.strip("<>")).query)
        self.assertEqual(["10"], links['rel="next"']["offset"])
        self.assertEqual(["0"], links['rel="prev"']["offset"])
        self.assertEqual(["5"], links['rel="next"']["limit"])
        # the filters of the request are kept in the links
        self.assertEqual(["solve_model_dag"], links['rel="next"']["schema"])

    def test_no_link_when_everything_fits_in_one_page(self):
        response = self.get(INSTANCE_URL, limit=50)
        self.assertEqual(ROWS, len(response.json))
        self.assertNotIn("Link", response.headers)

    def test_filters_change_the_total(self):
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        for url in (INSTANCE_URL, EXECUTION_URL):
            with self.subTest(url=url):
                self.assertEqual(ROWS, total(self.get(url, schema="solve_model_dag")))
                self.assertEqual(0, total(self.get(url, schema="another_dag")))
                self.assertEqual(
                    ROWS, total(self.get(url, creation_date_gte=yesterday))
                )
                self.assertEqual(0, total(self.get(url, creation_date_gte=tomorrow)))
                self.assertEqual(0, total(self.get(url, creation_date_lte=yesterday)))

    def test_deleted_rows_are_not_counted(self):
        response = self.client.delete(
            INSTANCE_URL + self.instance_ids[-1] + "/",
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(ROWS - 1, total(self.get(INSTANCE_URL)))

    def test_checks_and_kpis_executions_are_counted_only_when_asked(self):
        execution = ExecutionModel.query.first()
        execution.checks_and_kpis_only = True
        db.session.commit()
        self.assertEqual(ROWS - 1, total(self.get(EXECUTION_URL)))
        self.assertEqual(ROWS, total(self.get(EXECUTION_URL, checks_and_kpis=1)))

    def test_checks_only_executions_are_neither_listed_nor_counted(self):
        executions = ExecutionModel.query.order_by(ExecutionModel.id).all()
        for index, execution in enumerate(executions[:4]):
            execution.config = {**execution.config, "checks_only": index != 3}
        db.session.commit()
        listed = ROWS - 3
        limit = 4
        seen, offset = [], 0
        while True:
            response = self.get(EXECUTION_URL, limit=limit, offset=offset)
            page = response.json
            self.assertEqual(listed, total(response))
            seen += [row["id"] for row in page]
            offset += limit
            if offset >= total(response):
                break
            self.assertEqual(limit, len(page))
        self.assertEqual(listed, len(seen))
        self.assertEqual(listed, len(set(seen)))

    def test_cases_total(self):
        for _ in range(ROWS):
            self.create_new_row(CASE_URL, CaseModel, self.case_payload)
        response = self.get(CASE_URL)
        self.assertEqual(10, len(response.json))
        self.assertEqual(ROWS, total(response))

    def test_planner_total_counts_only_own_rows(self):
        previous = current_app.config["USER_ACCESS_ALL_OBJECTS"]
        current_app.config["USER_ACCESS_ALL_OBJECTS"] = 0
        try:
            other = self.create_planner()
            for _ in range(3):
                self.create_new_row(
                    INSTANCE_URL, InstanceModel, self.instance_payload, token=other
                )
            other_page = self.get(INSTANCE_URL, token=other)
            self.assertEqual(3, len(other_page.json))
            self.assertEqual(3, total(other_page))
            self.assertEqual(ROWS, total(self.get(INSTANCE_URL)))
        finally:
            current_app.config["USER_ACCESS_ALL_OBJECTS"] = previous

    def test_admin_total_counts_everybody(self):
        other = self.create_planner()
        self.create_new_row(
            INSTANCE_URL, InstanceModel, self.instance_payload, token=other
        )
        admin = self.create_admin()
        self.assertEqual(ROWS + 1, total(self.get(INSTANCE_URL, token=admin)))

    def test_cors_exposes_the_pagination_headers(self):
        response = self.client.get(
            INSTANCE_URL,
            headers={
                **self.get_header_with_auth(self.token),
                "Origin": "https://ui.example.com",
            },
        )
        exposed = response.headers["Access-Control-Expose-Headers"].split(", ")
        for header in ("X-Total-Count", "X-Offset", "X-Limit", "Link"):
            self.assertIn(header, exposed)


class TestListTotalPlatformIsolation(TestCase, _RoleUserMixin):
    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        with open(INSTANCE_PATH) as handler:
            self.payload = json.load(handler)
        self.client_token, _ = self.user_with_role(
            "clientplanner", "clientplanner@test.com", PLANNER_ROLE
        )
        self.admin_token, _ = self.user_with_role(
            "clientadmin", "clientadmin@test.com", ADMIN_ROLE
        )
        self.platform_token, _ = self.user_with_role(
            "platformplanner", "platformplanner@test.com", PLATFORM_PLANNER_ROLE
        )
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_instances(self, token, count):
        for _ in range(count):
            response = self.client.post(
                INSTANCE_URL, data=json.dumps(self.payload), headers=auth_header(token)
            )
            self.assertEqual(201, response.status_code)

    def test_client_admin_total_excludes_platform_rows(self):
        self.create_instances(self.platform_token, 4)
        self.create_instances(self.client_token, 11)
        response = self.client.get(INSTANCE_URL, headers=auth_header(self.admin_token))
        self.assertEqual(10, len(response.json))
        self.assertEqual("11", response.headers["X-Total-Count"])
