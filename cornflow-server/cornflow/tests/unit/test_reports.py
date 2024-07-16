"""
Unit test for the reports endpoints
"""

import shutil
import os
import json

from flask import current_app

from cornflow.models import ReportModel, InstanceModel, ExecutionModel
from cornflow.tests.const import (
    INSTANCE_PATH,
    REPORT_PATH,
    REPORT_HTML_FILE_PATH,
    REPORT_URL,
    INSTANCE_URL,
    EXECUTION_PATH,
    EXECUTION_URL_NORUN,
    REPORT_PDF_FILE_PATH,
)
from cornflow.tests.custom_test_case import CustomTestCase


class TestReportsListEndpoint(CustomTestCase):
    def setUp(self):
        # we create an instance, and an execution
        super().setUp()

        self.service_token = self.create_service_user()

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

        self.keys_to_check = [
            "id",
            "file_url",
            "name",
            "execution_id",
            "description",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

    def tearDown(self):
        super().tearDown()
        my_directories = os.listdir(current_app.config["UPLOAD_FOLDER"])
        for _dir in my_directories:
            try:
                shutil.rmtree(os.path.join(current_app.config["UPLOAD_FOLDER"], _dir))
            except OSError:
                pass

    def test_new_report_html(self):
        response = self.client.post(
            self.url,
            data=dict(file=(open(REPORT_HTML_FILE_PATH, "rb")), **self.payload),
            follow_redirects=True,
            headers=self.get_header_with_auth(
                self.service_token, content_type="multipart/form-data"
            ),
        )

        self.assertEqual(201, response.status_code)

        for key in self.keys_to_check:
            self.assertTrue(key in response.json)

        for key, value in self.payload.items():
            self.assertEqual(response.json[key], value)

        # check that the file in the test folder and the one generated on the static fodler are equal
        with open(REPORT_HTML_FILE_PATH, "rb") as f:
            file = f.read()
        my_upload_path = (
            f"{current_app.config['UPLOAD_FOLDER']}/"
            f"{self.payload['execution_id']}/{self.payload['name']}.html"
        )
        with open(my_upload_path, "rb") as f:
            file2 = f.read()

        self.assertEqual(file, file2)
        return response.json

    def test_new_report_pdf(self):
        response = self.client.post(
            self.url,
            data=dict(file=(open(REPORT_PDF_FILE_PATH, "rb")), **self.payload),
            follow_redirects=True,
            headers=self.get_header_with_auth(
                self.service_token, content_type="multipart/form-data"
            ),
        )

        self.assertEqual(201, response.status_code)

        for key in self.keys_to_check:
            self.assertTrue(key in response.json)

        for key, value in self.payload.items():
            self.assertEqual(response.json[key], value)

        # check that the file in the test folder and the one generated on the static fodler are equal
        with open(REPORT_PDF_FILE_PATH, "rb") as f:
            file = f.read()
        my_upload_path = (
            f"{current_app.config['UPLOAD_FOLDER']}/"
            f"{self.payload['execution_id']}/{self.payload['name']}.pdf"
        )
        with open(my_upload_path, "rb") as f:
            file2 = f.read()

        self.assertEqual(file, file2)
        return response.json

    def test_new_report_not_allowed(self):
        response = self.client.post(
            self.url,
            data=dict(file=(open(REPORT_HTML_FILE_PATH, "rb")), **self.payload),
            follow_redirects=True,
            headers=self.get_header_with_auth(
                self.token, content_type="multipart/form-data"
            ),
        )

        self.assertEqual(response.status_code, 403)

    def test_new_report_no_execution(self):
        payload = dict(self.payload)
        payload["execution_id"] = "bad_id"
        response = self.client.post(
            self.url,
            data=dict(file=(open(REPORT_HTML_FILE_PATH, "rb")), **payload),
            follow_redirects=True,
            headers=self.get_header_with_auth(
                self.service_token, content_type="multipart/form-data"
            ),
        )

        self.assertEqual(400, response.status_code)
        self.assertTrue("error" in response.json)

    def test_get_no_reports(self):
        self.get_no_rows(self.url)

    def test_get_all_reports(self):
        item = self.test_new_report_html()
        response = self.client.get(
            self.url, headers=self.get_header_with_auth(self.token)
        )

        self.assertEqual(1, len(response.json))
        self.assertEqual(item, response.json[0])

    def test_get_one_report(self):
        item = self.test_new_report_html()
        response = self.client.get(
            f"{self.url}{item['id']}/", headers=self.get_header_with_auth(self.token)
        )

        content = response.get_data()

        with open(REPORT_HTML_FILE_PATH, "rb") as f:
            file = f.read()

        self.assertEqual(200, response.status_code)
        self.assertEqual(content, file)

    def test_delete_report(self):
        item = self.test_new_report_html()
        response = self.client.delete(
            f"{self.url}{item['id']}/", headers=self.get_header_with_auth(self.token)
        )

        self.assertEqual(200, response.status_code)
        self.assertTrue("message" in response.json)

        my_upload_path = (
            f"{current_app.config['UPLOAD_FOLDER']}/"
            f"{self.payload['execution_id']}/{self.payload['name']}.html"
        )

        self.assertFalse(os.path.exists(my_upload_path))

        response = self.client.get(
            f"{self.url}{item['id']}/", headers=self.get_header_with_auth(self.token)
        )
        self.assertEqual(404, response.status_code)
