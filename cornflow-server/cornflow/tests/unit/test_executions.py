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
from sqlalchemy import event, inspect as sa_inspect
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
    DAG_URL,
    EXECUTION_FILES_CLEANUP_URL,
    EXECUTION_FILES_URL,
    EXECUTION_PATH,
    EXECUTION_SOLUTION_PATH,
    EXECUTION_URL,
    EXECUTION_URL_NORUN,
    INSTANCE_PATH,
    INSTANCE_URL,
)
from cornflow.shared.utils import hash_json_256
from cornflow.tests.custom_test_case import CustomTestCase
from cornflow.tests.unit.tools import patch_af_client, patch_db_client


# class AirflowPatcher:
#     @property
#     def orchestrator_patch_target(self):
#         return "cornflow.endpoints.execution.Airflow"
#
#     @property
#     def orchestrator_patch_fn(self):
#         return patch_af_client
#
#     def create_app(self):
#         return super().create_app()
#
#
# class DatabricksPatcher:
#     @property
#     def orchestrator_patch_target(self):
#         return "cornflow.endpoints.execution.Databricks"
#
#     @property
#     def orchestrator_patch_fn(self):
#         return patch_db_client
#
#     def create_app(self):
#         app = create_app("testing-databricks")
#         return app
#
#
# class TestExecutionsListEndpointAirflow(
#     AirflowPatcher, base_test_execution.BaseExecutionList
# ):
#     pass
#
#
# class TestExecutionsListEndpointDatabricks(
#     DatabricksPatcher, base_test_execution.BaseExecutionList
# ):
#     pass
#
#
# class TestExecutionRelaunchEndpointAirflow(
#     AirflowPatcher, base_test_execution.BaseExecutionRelaunch
# ):
#     pass
#
#
# class TestExecutionRelaunchEndpointDatabricks(
#     DatabricksPatcher, base_test_execution.BaseExecutionRelaunch
# ):
#     pass
#
#
# class TestExecutionsDetailEndpointAirflow(
#     AirflowPatcher, base_test_execution.BaseExecutionDetail
# ):
#     pass
#
#
# class TestExecutionsDetailEndpointDatabricks(
#     DatabricksPatcher, base_test_execution.BaseExecutionDetail
# ):
#     pass
#
#
# class TestExecutionsDataEndpointAirflow(
#     AirflowPatcher, base_test_execution.BaseExecutionData
# ):
#     pass
#
#
# class TestExecutionsDataEndpointDatabricks(
#     DatabricksPatcher, base_test_execution.BaseExecutionData
# ):
#     pass
#
#
# class TestExecutionsLogEndpointAirflow(
#     AirflowPatcher, base_test_execution.BaseExecutionLog
# ):
#     pass
#
#
# class TestExecutionsLogEndpointDatabricks(
#     DatabricksPatcher, base_test_execution.BaseExecutionLog
# ):
#     pass
#
#
# class TestExecutionsModelAirflow(
#     AirflowPatcher, base_test_execution.BaseExecutionModel
# ):
#     pass
#
#
# class TestExecutionsModelDatabricks(
#     DatabricksPatcher, base_test_execution.BaseExecutionModel
# ):
#     pass
#
#
# class TestExecutionsStatusEndpointAirflow(
#     AirflowPatcher, base_test_execution.BaseExecutionStatus
# ):
#     pass
#
#
# class TestExecutionsStatusEndpointDatabricks(
#     DatabricksPatcher, base_test_execution.BaseExecutionStatus
# ):
#     pass


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
        current_app.config["EXECUTION_FILES_CLEANUP_FREQUENCY"] = (
            self._original_cleanup_frequency
        )
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

        try:
            self.assertEqual(200, response.status_code)
            self.assertEqual("200", response.headers["X-Status-Code"])
            self.assertEqual(
                EXECUTION_FILES_STATUS_MESSAGE_DICT[EXECUTION_FILES_STATUS_OK],
                response.headers["X-Message"],
            )
            self.assertTrue(zipfile.is_zipfile(io.BytesIO(response.data)))
        finally:
            response.close()

    def test_get_non_ok_status_returns_status_error(self):
        """
        Validates that non-OK execution file statuses return a status payload.
        """
        self._set_execution_files_status(
            self.execution_id, EXECUTION_FILES_STATUS_NOT_UP_TO_DATE
        )

        response = self._get_execution_files()

        self.assertEqual(400, response.status_code)
        self.assertEqual(EXECUTION_FILES_STATUS_NOT_UP_TO_DATE, response.json["status"])
        self.assertEqual(
            EXECUTION_FILES_STATUS_MESSAGE_DICT[EXECUTION_FILES_STATUS_NOT_UP_TO_DATE],
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


class TestExecutionListDataLoading(CustomTestCase):
    """
    Tests that the execution list endpoint does not load heavy columns from the
    database and returns only the expected basic fields.
    """

    def setUp(self):
        super().setUp()
        # Load instance fixture and create a parent instance
        with open(INSTANCE_PATH) as f:
            instance_payload = json.load(f)
        self.instance_id = self.create_new_row(
            INSTANCE_URL, InstanceModel, instance_payload
        )

        # Load execution fixture and create the execution (without triggering a run)
        with open(EXECUTION_PATH) as f:
            execution_payload = json.load(f)
        execution_payload["instance_id"] = self.instance_id
        self.execution_id = self.create_new_row(
            EXECUTION_URL_NORUN, ExecutionModel, execution_payload
        )

        # Use a service user to push solution data into the execution via the DAG
        # endpoint so that the `data` column is non-NULL in the database.
        service_token = self.create_service_user()
        with open(EXECUTION_SOLUTION_PATH) as f:
            solution_data = json.load(f)
        self.update_row(
            url=DAG_URL + self.execution_id + "/",
            change={"data": solution_data},
            payload_to_check={},
            check_payload=False,
            token=service_token,
        )

    def _capture_queries_for_get_all_objects(self):
        captured_queries = []

        def _listener(conn, cursor, statement, parameters, context, executemany):
            captured_queries.append(statement)

        engine = db.engine
        event.listen(engine, "before_cursor_execute", _listener)
        try:
            executions = ExecutionModel.get_all_objects(user=self.user)
        finally:
            event.remove(engine, "before_cursor_execute", _listener)

        return executions, captured_queries

    def test_data_is_deferred_in_list_via_sqlalchemy_inspect(self):
        executions = ExecutionModel.get_all_objects(user=self.user)

        self.assertGreater(
            len(executions),
            0,
            "Expected at least one execution to be returned by get_all_objects",
        )

        for execution in executions:
            state = sa_inspect(execution)
            self.assertIn(
                "data",
                state.unloaded,
                "'data' should be deferred (not loaded eagerly) in the list query.",
            )

    def test_data_is_not_in_select_via_sql_interception(self):
        executions, captured_queries = self._capture_queries_for_get_all_objects()

        self.assertGreater(
            len(executions),
            0,
            "Expected at least one execution to be returned by get_all_objects",
        )

        self.assertTrue(
            len(captured_queries) > 0,
            "No SQL queries were captured; the event listener may not have fired.",
        )

        data_in_query = any(
            '"data"' in q or " data," in q.lower() or " data " in q.lower()
            for q in captured_queries
        )
        self.assertFalse(
            data_in_query,
            "The SELECT generated by get_all_objects must not include the 'data' column. "
            "Captured queries: " + str(captured_queries),
        )

    def test_list_endpoint_does_not_return_indicators(self):
        from cornflow.tests.const import EXECUTION_URL

        response = self.client.get(
            EXECUTION_URL,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(
            200,
            response.status_code,
            f"GET /execution/ returned unexpected status {response.status_code}",
        )

        items = response.json
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0, "Expected at least one execution in the list")

        for item in items:
            self.assertNotIn(
                "indicators",
                item,
                "'indicators' must not appear in execution list items.",
            )

    def test_list_endpoint_returns_basic_fields(self):
        from cornflow.tests.const import EXECUTION_URL

        response = self.client.get(
            EXECUTION_URL,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(200, response.status_code)

        items = response.json
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0, "Expected at least one execution in the list")

        required_fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
            "user_id",
            "username",
            "data_hash",
            "state",
            "message",
            "config",
            "instance_id",
            "schema",
            "log",
        ]

        for item in items:
            for field in required_fields:
                self.assertIn(
                    field,
                    item,
                    f"Required field '{field}' is missing from the execution list response.",
                )


class TestExecutionContractBaseline(CustomTestCase):
    """
    Contract tests for the endpoints that expose heavy JSON/TEXT columns
    (`data`, `checks`, `kpis`, `log_text`, `log_json`) on instances and
    executions.

    These tests pin the exact response shape and the stability of
    `data_hash`, so any internal change to how those columns are loaded or
    serialized can be verified to leave client-observable behavior unchanged.
    """

    def setUp(self):
        super().setUp()
        with open(INSTANCE_PATH) as f:
            instance_payload = json.load(f)
        self.instance_id = self.create_new_row(
            INSTANCE_URL, InstanceModel, instance_payload
        )

        with open(EXECUTION_PATH) as f:
            execution_payload = json.load(f)
        execution_payload["instance_id"] = self.instance_id
        self.execution_id = self.create_new_row(
            EXECUTION_URL_NORUN, ExecutionModel, execution_payload
        )

        # Push solution data (data/checks/kpis/log) into the execution via the
        # DAG endpoint (service user) so that every heavy column is populated
        # and observable in the baseline snapshots.
        service_token = self.create_service_user()
        with open(EXECUTION_SOLUTION_PATH) as f:
            solution_data = json.load(f)

        self.reference_data = solution_data
        self.reference_data_hash = hash_json_256(solution_data)

        self.update_row(
            url=DAG_URL + self.execution_id + "/",
            change={
                "data": solution_data,
                "checks": {"check_1": {"result": True, "detail": "ok"}},
            },
            payload_to_check={},
            check_payload=False,
            token=service_token,
        )

    @staticmethod
    def _capture_queries(callable_under_test):
        captured_queries = []

        def _listener(conn, cursor, statement, parameters, context, executemany):
            captured_queries.append(statement)

        engine = db.engine
        event.listen(engine, "before_cursor_execute", _listener)
        try:
            result = callable_under_test()
        finally:
            event.remove(engine, "before_cursor_execute", _listener)

        return result, captured_queries

    @staticmethod
    def _select_includes_column(queries, column_name):
        needle_variants = [
            f'"{column_name}"',
            f" {column_name},",
            f" {column_name} ",
            f".{column_name}",
        ]
        return any(
            any(variant in q for variant in needle_variants) for q in queries
        )

    # region contract/baseline snapshots

    def test_baseline_execution_data_endpoint_contract(self):
        """
        `GET /execution/{id}/data/` must return `id`, `data`, `checks`,
        `kpis` and `log`, with `data` byte/shape-identical to what was
        stored.
        """
        response = self.client.get(
            EXECUTION_URL + self.execution_id + "/data/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(200, response.status_code)
        body = response.json

        for field in ["id", "data", "checks", "kpis", "log"]:
            self.assertIn(field, body)

        self.assertEqual(self.execution_id, body["id"])
        self.assertEqual(
            self.reference_data,
            body["data"],
            "The 'data' field returned by GET /execution/{id}/data/ must be "
            "byte/shape-identical to what was stored.",
        )

    def test_baseline_instance_data_endpoint_contract(self):
        """
        `GET /instance/{id}/data/` must return `id`, `data` and `checks`.
        """
        response = self.client.get(
            INSTANCE_URL + self.instance_id + "/data/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(200, response.status_code)
        body = response.json

        for field in ["id", "data", "checks"]:
            self.assertIn(field, body)
        self.assertEqual(self.instance_id, body["id"])

    def test_baseline_execution_log_endpoint_contract(self):
        """
        `GET /execution/{id}/log/` must return `id` and `log`.
        """
        response = self.client.get(
            EXECUTION_URL + self.execution_id + "/log/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(200, response.status_code)
        body = response.json
        self.assertIn("id", body)
        self.assertIn("log", body)

    def test_baseline_execution_status_endpoint_contract(self):
        """
        `GET /execution/{id}/status/` must return only `id`, `state`,
        `message` and `data_hash`; it must never expose `data`, `checks`,
        `kpis`, `log`, `log_text` or `log_json`.
        """
        response = self.client.get(
            EXECUTION_URL + self.execution_id + "/status/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(200, response.status_code)
        body = response.json

        for field in ["id", "state", "message", "data_hash"]:
            self.assertIn(field, body)
        for field in ["data", "checks", "kpis", "log", "log_text", "log_json"]:
            self.assertNotIn(field, body)

    def test_baseline_execution_detail_endpoint_contract(self):
        """
        `GET /execution/{id}/` must expose the standard metadata fields and
        must never include `data` or `indicators`.
        """
        response = self.client.get(
            EXECUTION_URL + self.execution_id + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(200, response.status_code)
        body = response.json

        for field in [
            "id",
            "name",
            "description",
            "data_hash",
            "state",
            "message",
            "instance_id",
            "schema",
        ]:
            self.assertIn(field, body)
        self.assertNotIn("data", body)
        self.assertNotIn("indicators", body)

    def test_baseline_instance_detail_endpoint_contract(self):
        """
        `GET /instance/{id}/` must expose the standard metadata fields and
        must never include `data`.
        """
        response = self.client.get(
            INSTANCE_URL + self.instance_id + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(200, response.status_code)
        body = response.json

        for field in ["id", "name", "description", "data_hash", "schema"]:
            self.assertIn(field, body)
        self.assertNotIn("data", body)

    # endregion

    # region data_hash stability

    def test_data_hash_is_stable_for_reference_payload(self):
        """
        `hash_json_256` must be deterministic/reproducible for the same
        `data` payload.
        """
        hash_1 = hash_json_256(self.reference_data)
        hash_2 = hash_json_256(self.reference_data)
        self.assertEqual(hash_1, hash_2)
        self.assertEqual(self.reference_data_hash, hash_1)

    def test_data_hash_matches_instance_creation_payload(self):
        """
        `data_hash` for an instance created via `POST /instance/` must match
        `hash_json_256` computed locally on the exact `data` payload sent by
        the client.
        """
        with open(INSTANCE_PATH) as f:
            instance_payload = json.load(f)

        response = self.client.get(
            INSTANCE_URL + self.instance_id + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(200, response.status_code)
        expected_hash = hash_json_256(instance_payload["data"])
        self.assertEqual(expected_hash, response.json["data_hash"])

    def test_data_hash_is_not_recomputed_when_dag_endpoint_writes_solution(self):
        """
        Documents current behavior: `ExecutionModel.data_hash` is only
        computed once, in `BaseDataModel.__init__` at creation time.
        `BaseDataModel.update()` (used by `DAGDetailEndpoint.put` to write
        the solution `data`) does a
        plain `setattr` per field and never recalculates `data_hash`.

        As a result, `data_hash` on `GET /execution/{id}/status/` reflects
        the hash of the `data` payload sent at creation time (`None`/absent
        for a `run=0` execution created without a solution), NOT the hash of
        the solution `data` written later via the DAG endpoint. Clients may
        already depend on this behavior, so it must be preserved unless a
        change is deliberately scoped and documented.
        """
        response = self.client.get(
            EXECUTION_URL + self.execution_id + "/status/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(200, response.status_code)

        hash_of_creation_payload = hash_json_256(None)
        self.assertEqual(hash_of_creation_payload, response.json["data_hash"])
        self.assertNotEqual(self.reference_data_hash, response.json["data_hash"])

    # endregion

    # region SQL-level column loading

    def test_status_endpoint_query_does_not_defer_data_and_log_columns(self):
        """
        `GET /execution/{id}/status/` must not load `data`, `log_text` or
        `log_json` in its SELECT: the response schema never serializes them.
        """

        def _call_status_endpoint():
            return self.client.get(
                EXECUTION_URL + self.execution_id + "/status/",
                follow_redirects=True,
                headers=self.get_header_with_auth(self.token),
            )

        response, captured_queries = self._capture_queries(_call_status_endpoint)
        self.assertEqual(200, response.status_code)
        self.assertGreater(
            len(captured_queries),
            0,
            "No SQL queries were captured; the event listener may not have fired.",
        )

        deferred_columns = ["data", "log_text", "log_json"]
        columns_in_select = {
            column: self._select_includes_column(captured_queries, column)
            for column in deferred_columns
        }

        self.assertFalse(
            any(columns_in_select.values()),
            "GET /execution/{id}/status/ must not load data/log_text/log_json "
            f"in its SELECT. Columns found in SELECT: {columns_in_select}. "
            f"Captured queries: {captured_queries}",
        )

    # TODO(remove-before-merge): temporary coverage gap tracker. Both
    # `checks` and `kpis` are still loaded by `ExecutionModel.get_one_object`
    # even with `defer_data=True`, including by `GET /execution/{id}/status/`
    # and `ExecutionDetailsEndpoint.get`. Once `get_one_object` also defers
    # `checks`/`kpis`, drop this test (its assertion becomes part of
    # `test_status_endpoint_query_does_not_defer_data_and_log_columns` and of
    # a similar check on `ExecutionModel.get_one_object` directly) instead of
    # keeping it as a documented gap.
    def test_get_one_object_defer_data_does_not_defer_checks_and_kpis_YET(self):
        """
        `ExecutionModel.get_one_object(defer_data=True)` only defers `data`,
        `log_text` and `log_json`; it never defers `checks` nor `kpis`, so
        any caller using `defer_data=True` still loads a potentially large
        `checks`/`kpis` blob into memory. Currently FAILS, documenting a
        known gap; must pass once `checks`/`kpis` are added to the defer
        list.
        """

        def _call_get_one_object():
            return ExecutionModel.get_one_object(
                user=self.user, idx=self.execution_id, defer_data=True
            )

        execution, captured_queries = self._capture_queries(_call_get_one_object)
        self.assertIsNotNone(execution)
        self.assertGreater(
            len(captured_queries),
            0,
            "No SQL queries were captured; the event listener may not have fired.",
        )

        gap_columns = ["checks", "kpis"]
        columns_in_select = {
            column: self._select_includes_column(captured_queries, column)
            for column in gap_columns
        }

        self.assertFalse(
            any(columns_in_select.values()),
            "ExecutionModel.get_one_object(defer_data=True) must defer "
            "'checks' and 'kpis' too, not just 'data'/'log_text'/'log_json'. "
            f"Columns found in SELECT: {columns_in_select}. "
            f"Captured queries: {captured_queries}",
        )

    def test_data_endpoint_query_loads_data_and_checks_and_kpis(self):
        """
        `GET /execution/{id}/data/` must load `data`, `checks` and `kpis`,
        since it serializes all three in the response.
        """

        def _call_data_endpoint():
            return self.client.get(
                EXECUTION_URL + self.execution_id + "/data/",
                follow_redirects=True,
                headers=self.get_header_with_auth(self.token),
            )

        response, captured_queries = self._capture_queries(_call_data_endpoint)
        self.assertEqual(200, response.status_code)

        heavy_columns = ["data", "checks", "kpis"]
        columns_in_select = {
            column: self._select_includes_column(captured_queries, column)
            for column in heavy_columns
        }
        self.assertTrue(
            all(columns_in_select.values()),
            "Expected GET /execution/{id}/data/ to load data/checks/kpis. "
            f"Found: {columns_in_select}. Captured queries: {captured_queries}",
        )

    # endregion
