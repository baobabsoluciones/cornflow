"""
Unit test for the executions endpoints
"""

# Import from libraries
import io
import json
import os
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from flask import current_app
from cornflow.app import create_app
from cornflow.tests import base_test_execution

# Import from internal modules
from cornflow.models import ExecutionModel, InstanceModel
from cornflow.shared import db
from cornflow.shared.const import (
    ADMIN_ROLE,
    EXECUTION_FILES_STATUS_DELETED,
    EXECUTION_FILES_STATUS_ERROR,
    EXECUTION_FILES_STATUS_NOT_GENERATED,
    EXECUTION_FILES_STATUS_NOT_UP_TO_DATE,
    EXECUTION_FILES_STATUS_OK,
    EXECUTION_FILES_STATUS_MESSAGE_DICT,
    PLANNER_ROLE,
    VIEWER_ROLE,
)
from cornflow.tests.const import (
    EXECUTION_FILES_CLEANUP_URL,
    EXECUTION_FILES_URL,
    EXECUTION_PATH,
    EXECUTION_URL_NORUN,
    INSTANCE_PATH,
    INSTANCE_URL,
)
from cornflow.tests.custom_test_case import CustomTestCase
from cornflow.tests.unit.tools import patch_af_client, patch_db_client


class AirflowPatcher:
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Airflow"

    @property
    def orchestrator_patch_fn(self):
        return patch_af_client

    def create_app(self):
        return super().create_app()


class DatabricksPatcher:
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Databricks"

    @property
    def orchestrator_patch_fn(self):
        return patch_db_client

    def create_app(self):
        app = create_app("testing-databricks")
        return app


class TestExecutionsListEndpointAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionList
):
    pass


class TestExecutionsListEndpointDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionList
):
    pass


class TestExecutionRelaunchEndpointAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionRelaunch
):
    pass


class TestExecutionRelaunchEndpointDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionRelaunch
):
    pass


class TestExecutionsDetailEndpointAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionDetail
):
    pass


class TestExecutionsDetailEndpointDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionDetail
):
    pass


class TestExecutionsDataEndpointAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionData
):
    pass


class TestExecutionsDataEndpointDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionData
):
    pass


class TestExecutionsLogEndpointAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionLog
):
    pass


class TestExecutionsLogEndpointDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionLog
):
    pass


class TestExecutionsModelAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionModel
):
    pass


class TestExecutionsModelDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionModel
):
    pass


class TestExecutionsStatusEndpointAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionStatus
):
    pass


class TestExecutionsStatusEndpointDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionStatus
):
    pass


class TestExecutionFilesEndpoint(CustomTestCase):
    """
    Tests for the execution files endpoints.
    """

    # region helpers

    def setUp(self):
        super().setUp()
        with open(INSTANCE_PATH) as f:
            instance_payload = json.load(f)
        instance_id = self.create_new_row(INSTANCE_URL, InstanceModel, instance_payload)

        with open(EXECUTION_PATH) as f:
            self.payload = json.load(f)
        self.payload["instance_id"] = instance_id
        self.execution_id = self.create_new_row(
            EXECUTION_URL_NORUN, ExecutionModel, self.payload
        )
        self.service_token = self.create_service_user()

        self._original_execution_files = current_app.config["EXECUTION_FILES"]
        self._original_execution_files_path = current_app.config["EXECUTION_FILES_PATH"]
        self._original_cleanup_frequency = current_app.config[
            "EXECUTION_FILES_CLEANUP_FREQUENCY"
        ]
        self.temp_dir = tempfile.TemporaryDirectory()
        current_app.config["EXECUTION_FILES"] = 1
        current_app.config["EXECUTION_FILES_PATH"] = self.temp_dir.name
        current_app.config["EXECUTION_FILES_CLEANUP_FREQUENCY"] = 30

    def tearDown(self):
        current_app.config["EXECUTION_FILES"] = self._original_execution_files
        current_app.config["EXECUTION_FILES_PATH"] = self._original_execution_files_path
        current_app.config[
            "EXECUTION_FILES_CLEANUP_FREQUENCY"
        ] = self._original_cleanup_frequency
        self.temp_dir.cleanup()
        super().tearDown()

    @staticmethod
    def _multipart_auth_header(token):
        return {"Authorization": "Bearer " + token}

    @staticmethod
    def _zip_buffer(filename="output.txt", content=b"ok"):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zip_file:
            zip_file.writestr(filename, content)
        buffer.seek(0)
        return buffer

    def _assert_no_file_is_returned(self, response):
        self.assertNotIn("Content-Disposition", response.headers)
        self.assertFalse(zipfile.is_zipfile(io.BytesIO(response.data)))

    def _execution_files_path(self, execution_id=None):
        execution_id = execution_id or self.execution_id
        return os.path.join(
            current_app.config["EXECUTION_FILES_PATH"], f"{execution_id}.zip"
        )

    def _post_execution_files(
        self,
        execution_id=None,
        status=EXECUTION_FILES_STATUS_OK,
        file_buffer=None,
        filename="execution.zip",
        token=None,
    ):
        execution_id = execution_id or self.execution_id
        token = token or self.service_token
        data = {"execution_files_status": str(status)}
        if file_buffer is not None:
            data["execution_file"] = (file_buffer, filename)

        return self.client.post(
            EXECUTION_FILES_URL + execution_id + "/",
            data=data,
            follow_redirects=True,
            headers=self._multipart_auth_header(token),
            content_type="multipart/form-data",
        )

    def _get_execution_files(self, execution_id=None, token=None):
        execution_id = execution_id or self.execution_id
        token = token or self.token
        return self.client.get(
            EXECUTION_FILES_URL + execution_id + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(token),
        )

    def _delete_execution_files(self, token=None):
        token = token or self.service_token
        return self.client.delete(
            EXECUTION_FILES_CLEANUP_URL,
            follow_redirects=True,
            headers=self.get_header_with_auth(token),
        )

    def _create_execution_file(self, execution_id=None):
        execution_id = execution_id or self.execution_id
        path = self._execution_files_path(execution_id)
        with open(path, "wb") as fd:
            fd.write(self._zip_buffer().getvalue())
        return path

    @staticmethod
    def _set_execution_files_status(execution_id, status):
        execution = ExecutionModel.get_one_object(idx=execution_id)
        execution.update({"execution_files_status": status})
        return execution

    # endregion

    # region POST endpoint tests

    def test_post_valid_zip_saves_file_and_status(self):
        """
        Validates that a service user can upload a valid zip and mark files as ready.
        """
        response = self._post_execution_files(file_buffer=self._zip_buffer())

        self.assertEqual(200, response.status_code)
        self.assertEqual("Execution files saved correctly", response.json["message"])
        self.assertTrue(os.path.exists(self._execution_files_path()))
        self.assertTrue(zipfile.is_zipfile(self._execution_files_path()))
        execution = ExecutionModel.get_one_object(idx=self.execution_id)
        self.assertEqual(EXECUTION_FILES_STATUS_OK, execution.execution_files_status)

    def test_post_non_ok_status_does_not_require_file(self):
        """
        Validates that non-OK statuses can be stored without an uploaded file.
        """
        statuses = [
            EXECUTION_FILES_STATUS_ERROR,
            EXECUTION_FILES_STATUS_DELETED,
            EXECUTION_FILES_STATUS_NOT_GENERATED,
            EXECUTION_FILES_STATUS_NOT_UP_TO_DATE,
        ]

        for status in statuses:
            response = self._post_execution_files(status=status)

            self.assertEqual(200, response.status_code)
            self.assertEqual(
                "Execution files status saved correctly", response.json["message"]
            )
            self.assertFalse(os.path.exists(self._execution_files_path()))
            execution = ExecutionModel.get_one_object(idx=self.execution_id)
            self.assertEqual(status, execution.execution_files_status)

    def test_post_ok_status_requires_file(self):
        """
        Validates that an OK status without a zip file is rejected.
        """
        response = self._post_execution_files()

        self.assertEqual(400, response.status_code)
        self.assertFalse(os.path.exists(self._execution_files_path()))
        execution = ExecutionModel.get_one_object(idx=self.execution_id)
        self.assertEqual(
            EXECUTION_FILES_STATUS_NOT_GENERATED, execution.execution_files_status
        )

    def test_post_ok_status_rejects_invalid_zip(self):
        """
        Validates that an OK status with invalid zip content is rejected.
        """
        response = self._post_execution_files(
            file_buffer=io.BytesIO(b"not a zip"), filename="execution.zip"
        )

        self.assertEqual(400, response.status_code)
        self.assertFalse(os.path.exists(self._execution_files_path()))
        execution = ExecutionModel.get_one_object(idx=self.execution_id)
        self.assertEqual(
            EXECUTION_FILES_STATUS_NOT_GENERATED, execution.execution_files_status
        )

    def test_post_unknown_execution_returns_not_found(self):
        """
        Validates that posting files for an unknown execution returns a not-found error.
        """
        response = self._post_execution_files(
            execution_id="unknown", file_buffer=self._zip_buffer()
        )

        self.assertEqual(404, response.status_code)

    def test_post_is_service_only(self):
        """
        Validates that only service users can post execution files.
        """
        viewer_token = self.create_user_with_role(VIEWER_ROLE)
        planner_token = self.create_user_with_role(PLANNER_ROLE)
        admin_token = self.create_user_with_role(ADMIN_ROLE)

        for token in [self.token, viewer_token, planner_token, admin_token]:
            response = self._post_execution_files(
                file_buffer=self._zip_buffer(), token=token
            )
            self.assertEqual(403, response.status_code)

        response = self._post_execution_files(file_buffer=self._zip_buffer())
        self.assertEqual(200, response.status_code)
        self.assertEqual("Execution files saved correctly", response.json["message"])

    # endregion

    # region GET endpoint tests

    def test_get_valid_zip(self):
        """
        Validates that a ready execution returns the stored zip file.
        """
        self._create_execution_file()
        self._set_execution_files_status(self.execution_id, EXECUTION_FILES_STATUS_OK)

        response = self._get_execution_files()

        self.assertEqual(200, response.status_code)
        self.assertEqual("200", response.headers["X-Status-Code"])
        self.assertEqual(
            EXECUTION_FILES_STATUS_MESSAGE_DICT[EXECUTION_FILES_STATUS_OK],
            response.headers["X-Message"],
        )
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(response.data)))

    def test_get_non_ok_status_returns_status_error(self):
        """
        Validates that non-OK execution file statuses return a status payload.
        """
        self._set_execution_files_status(
            self.execution_id, EXECUTION_FILES_STATUS_NOT_UP_TO_DATE
        )

        response = self._get_execution_files()

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            EXECUTION_FILES_STATUS_NOT_UP_TO_DATE, response.json["status"]
        )
        self.assertEqual(
            EXECUTION_FILES_STATUS_MESSAGE_DICT[
                EXECUTION_FILES_STATUS_NOT_UP_TO_DATE
            ],
            response.json["error"],
        )
        self.assertNotIn("message", response.json)
        self._assert_no_file_is_returned(response)

    def test_get_missing_file_marks_status_as_deleted(self):
        """
        Validates that a missing zip for an OK execution marks files as deleted.
        """
        self._set_execution_files_status(self.execution_id, EXECUTION_FILES_STATUS_OK)

        response = self._get_execution_files()

        self.assertEqual(400, response.status_code)
        self.assertEqual(EXECUTION_FILES_STATUS_DELETED, response.json["status"])
        self.assertEqual(
            EXECUTION_FILES_STATUS_MESSAGE_DICT[EXECUTION_FILES_STATUS_DELETED],
            response.json["error"],
        )
        self.assertNotIn("message", response.json)
        self._assert_no_file_is_returned(response)
        execution = ExecutionModel.get_one_object(idx=self.execution_id)
        self.assertEqual(
            EXECUTION_FILES_STATUS_DELETED, execution.execution_files_status
        )

    def test_execution_files_disabled_returns_not_implemented(self):
        """
        Validates that file endpoints are unavailable when execution files are disabled.
        """
        current_app.config["EXECUTION_FILES"] = 0

        get_response = self._get_execution_files()
        post_response = self._post_execution_files(file_buffer=self._zip_buffer())

        self.assertEqual(501, get_response.status_code)
        self.assertEqual(501, post_response.status_code)
        self._assert_no_file_is_returned(get_response)

    # endregion

    # region cleanup endpoint tests

    def test_cleanup_deletes_old_and_orphan_zip_files(self):
        """
        Validates that cleanup removes old and orphan zips while keeping recent files.
        """
        recent_path = self._create_execution_file(self.execution_id)
        self._set_execution_files_status(self.execution_id, EXECUTION_FILES_STATUS_OK)

        old_execution_id = self.create_new_row(
            EXECUTION_URL_NORUN, ExecutionModel, self.payload
        )
        old_path = self._create_execution_file(old_execution_id)
        old_execution = self._set_execution_files_status(
            old_execution_id, EXECUTION_FILES_STATUS_OK
        )
        old_execution.updated_at = datetime.now(timezone.utc) - timedelta(days=31)
        db.session.add(old_execution)
        db.session.commit()

        orphan_path = self._execution_files_path("orphan")
        with open(orphan_path, "wb") as fd:
            fd.write(self._zip_buffer().getvalue())

        response = self._delete_execution_files()

        self.assertEqual(200, response.status_code)
        self.assertEqual("2 files were deleted.", response.json["message"])
        self.assertTrue(os.path.exists(recent_path))
        self.assertFalse(os.path.exists(old_path))
        self.assertFalse(os.path.exists(orphan_path))
        old_execution = ExecutionModel.get_one_object(idx=old_execution_id)
        self.assertEqual(
            EXECUTION_FILES_STATUS_DELETED, old_execution.execution_files_status
        )

    def test_cleanup_is_service_only(self):
        """
        Validates that only service users can run execution files cleanup.
        """
        admin_token = self.create_admin()
        planner_token = self.create_planner()

        for token in [self.token, planner_token, admin_token]:
            response = self._delete_execution_files(token=token)
            self.assertEqual(403, response.status_code)

        response = self._delete_execution_files()
        self.assertEqual(200, response.status_code)
        self.assertEqual("0 files were deleted.", response.json["message"])

    # endregion
