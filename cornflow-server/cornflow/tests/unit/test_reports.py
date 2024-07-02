"""
Unit test for the reports endpoints
"""
import json

from flask import current_app

from cornflow.models import ReportModel, InstanceModel, ExecutionModel
from cornflow.tests.const import (
    INSTANCE_PATH,
    REPORT_PATH,
    REPORT_FILE_PATH,
    REPORT_URL,
    INSTANCE_URL,
    EXECUTION_PATH,
    EXECUTION_URL_NORUN,
)
from cornflow.tests.custom_test_case import CustomTestCase


class TestReportsListEndpoint(CustomTestCase):
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
        response = self.client.post(
            self.url,
            data=dict(file=(open(REPORT_FILE_PATH, "rb")), **self.payload),
            follow_redirects=True,
            headers=self.get_header_with_auth(
                self.token, content_type="multipart/form-data"
            ),
        )

        self.assertEqual(201, response.status_code)
        self.assertTrue("message" in response.json)

        # check that the file in the test folder and the one generated on the static fodler are equal
        with open(REPORT_FILE_PATH, "rb") as f:
            file = f.read()
        with open(
            f"{current_app.config['UPLOAD_FOLDER']}/{self.payload['name']}.html", "rb"
        ) as f:
            file2 = f.read()

        self.assertEqual(file, file2)

    def test_new_report_no_execution(self):
        payload = dict(self.payload)
        payload["execution_id"] = "bad_id"
        response = self.client.post(
            self.url,
            data=dict(file=(open(REPORT_FILE_PATH, "rb")), **payload),
            follow_redirects=True,
            headers=self.get_header_with_auth(
                self.token, content_type="multipart/form-data"
            ),
        )

        print(response.json)

        self.assertEqual(400, response.status_code)
        self.assertTrue("error" in response.json)

    def test_get_no_reports(self):
        self.get_no_rows(self.url)
