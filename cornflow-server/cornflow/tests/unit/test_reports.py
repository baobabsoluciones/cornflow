"""
Unit test for the reports endpoints
"""

# Import from libraries
import json
from unittest.mock import patch

# Import from internal modules
from cornflow.models import ReportModel, InstanceModel, ExecutionModel
from cornflow.tests.const import (
    INSTANCE_PATH,
    REPORT_PATH,
    REPORT_URL,
    INSTANCE_URL,
    EXECUTION_PATH,
    DAG_URL,
    BAD_REPORT_PATH,
    EXECUTION_URL_NORUN,
)
from cornflow.tests.custom_test_case import CustomTestCase, BaseTestCases
from cornflow.tests.unit.tools import patch_af_client


class TestReportsListEndpoint(BaseTestCases.ListFilters):
    def setUp(self):
        # we create an instance, and an execution
        super().setUp()

        # instance:
        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        fk_id = self.create_new_row(INSTANCE_URL, InstanceModel, payload)

        def load_file_fk(_file, **kwargs):
            with open(_file) as f:
                temp = json.load(f)
            temp.update(kwargs)
            return temp

        # execution:
        fk_id = self.create_new_row(
            EXECUTION_URL_NORUN,
            ExecutionModel,
            payload=load_file_fk(EXECUTION_PATH, instance_id=fk_id),
        )

        self.payload = load_file_fk(REPORT_PATH, execution_id=fk_id)

        self.url = REPORT_URL
        self.model = ReportModel

        # self.payloads = [load_file_fk(f) for f in REPORTS_LIST]
        # self.solution = load_file_fk(EXECUTION_SOLUTION_PATH)
        self.keys_to_check = [
            "id",
            "file_url",
            "name",
            "user_id",
            "execution_id",
            "description",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

    def test_new_report(self):
        self.create_new_row(self.url, self.model, payload=self.payload)

    def test_new_report_no_execution(self):
        payload = dict(self.payload)
        payload["execution_id"] = "bad_id"
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(404, response.status_code)
        self.assertTrue("error" in response.json)

    def test_get_no_reports(self):
        self.get_no_rows(self.url)

    def test_repr_method(self):
        idx = self.create_new_row(self.url, self.model, self.payload)
        self.repr_method(idx, f"<Report {idx}>")

    def test_str_method(self):
        idx = self.create_new_row(self.url, self.model, self.payload)
        self.str_method(idx, f"<Report {idx}>")
