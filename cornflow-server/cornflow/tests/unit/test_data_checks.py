"""
Unit tests for the data check endpoints.

This module contains tests for data validation functionality, including:

- Execution data checks
- Instance data validation
- Case data verification
- Airflow integration testing
- Run and no-run scenarios
- Response validation

The tests verify both successful validation operations and proper error handling
for various data check scenarios.
"""

# Import from libraries
import json
from unittest.mock import patch

from flask import current_app

# Import from internal modules
from cornflow.models import ExecutionModel, InstanceModel, CaseModel
from cornflow.shared.const import (
    EXEC_STATE_ERROR_START,
    EXEC_STATE_QUEUED,
    PULSE_BACKEND,
)
from cornflow.tests.const import (
    INSTANCE_PATH,
    EXECUTION_PATH,
    CASE_PATH,
    EXECUTION_URL,
    EXECUTION_URL_NORUN,
    DATA_CHECK_EXECUTION_URL,
    DATA_CHECK_INSTANCE_URL,
    DATA_CHECK_CASE_URL,
    INSTANCE_URL,
    CASE_URL,
)
from cornflow.tests.custom_test_case import CustomTestCase
from cornflow.tests.unit.tools import patch_af_client


class TestDataChecksExecutionEndpoint(CustomTestCase):
    """
    Test suite for execution data check endpoints.

    This class tests data validation for executions:

    - Direct execution checks
    - Run and no-run validation scenarios
    - Response structure validation
    - Airflow integration testing
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes:

        - Base test configuration
        - Test instance data
        - Execution model
        - Test payload
        """
        super().setUp()

        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        fk_id = self.create_new_row(INSTANCE_URL, InstanceModel, payload)
        self.model = ExecutionModel

        def load_file_fk(_file):
            with open(_file) as f:
                temp = json.load(f)
            temp["instance_id"] = fk_id
            return temp

        self.payload = load_file_fk(EXECUTION_PATH)

    def test_check_execution(self):
        """
        Test execution data check without running.

        Verifies:

        - Successful data check creation
        - Correct response status
        - Proper ID assignment
        - Data consistency
        """
        exec_to_check_id = self.create_new_row(
            EXECUTION_URL_NORUN, self.model, payload=self.payload
        )
        url = DATA_CHECK_EXECUTION_URL + exec_to_check_id + "/?run=0"
        response = self.client.post(
            url,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(201, response.status_code)
        response = response.json

        row = self.model.query.get(response["id"])
        self.assertEqual(row.id, response["id"])
        self.assertEqual(row.id, exec_to_check_id)

    @patch("cornflow.endpoints.data_check.Airflow")
    def test_check_execution_run(self, af_client_class):
        """
        Test execution data check with Airflow integration.

        Verifies:

        - Successful data check creation
        - Airflow client interaction
        - Response validation
        - Data consistency
        """
        patch_af_client(af_client_class)

        exec_to_check_id = self.create_new_row(
            EXECUTION_URL_NORUN, self.model, payload=self.payload
        )

        url = DATA_CHECK_EXECUTION_URL + exec_to_check_id + "/"
        response = self.client.post(
            url,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(201, response.status_code)
        response = response.json

        row = self.model.query.get(response["id"])
        self.assertEqual(row.id, response["id"])
        self.assertEqual(row.id, exec_to_check_id)


class TestDataChecksInstanceEndpoint(CustomTestCase):
    """
    Test suite for instance data check endpoints.

    This class tests data validation for instances:

    - Instance data validation
    - Run and no-run scenarios
    - Configuration verification
    - Response structure validation
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes:

        - Base test configuration
        - Test instance data
        - Instance ID reference
        - Execution model
        """
        super().setUp()

        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        fk_id = self.create_new_row(INSTANCE_URL, InstanceModel, payload)
        self.instance_id = fk_id
        self.model = ExecutionModel

    def test_new_data_check_execution(self):
        """
        Test instance data check without running.

        Verifies:

        - Successful data check creation
        - Correct response status
        - Instance ID association
        - Configuration settings
        - New execution is not returned by get_all_executions
        """
        url = DATA_CHECK_INSTANCE_URL + self.instance_id + "/?run=0"
        response = self.client.post(
            url,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(201, response.status_code)
        response = response.json

        row = self.model.query.get(response["id"])
        self.assertEqual(row.id, response["id"])

        self.assertEqual(row.instance_id, self.instance_id)
        self.assertTrue(row.config.get("checks_and_kpis_only"))
        self.assertTrue(row.checks_and_kpis_only)

        response = self.client.get(
            EXECUTION_URL,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 0)

        response = self.client.get(
            f"{EXECUTION_URL}?checks_and_kpis=true",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)

    @patch("cornflow.endpoints.data_check.Airflow")
    def test_new_data_check_execution_run(self, af_client_class):
        """
        Test instance data check with Airflow integration.

        Verifies:

        - Successful data check creation
        - Airflow client interaction
        - Instance association
        - Configuration validation
        """
        patch_af_client(af_client_class)

        url = DATA_CHECK_INSTANCE_URL + self.instance_id + "/"
        response = self.client.post(
            url,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(201, response.status_code)
        response = response.json

        row = self.model.query.get(response["id"])
        self.assertEqual(row.id, response["id"])

        self.assertEqual(row.instance_id, self.instance_id)
        self.assertTrue(row.config.get("checks_and_kpis_only"))
        self.assertTrue(row.checks_and_kpis_only)


class TestDataChecksCaseEndpoint(CustomTestCase):
    """
    Test suite for case data check endpoints.

    This class tests data validation for cases:

    - Case data validation
    - Run and no-run scenarios
    - Configuration verification
    - Response structure validation
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes:

        - Base test configuration
        - Test case data
        - Case ID reference
        - Execution model
        """
        super().setUp()

        with open(CASE_PATH) as f:
            payload = json.load(f)
        case_id = self.create_new_row(CASE_URL, CaseModel, payload)
        self.case_id = case_id
        self.model = ExecutionModel

    def test_new_data_check_execution(self):
        """
        Test case data check without running.

        Verifies:

        - Successful data check creation
        - Correct response status
        - Configuration settings
        - Response validation
        - New execution is not returned by get_all_executions
        """
        url = DATA_CHECK_CASE_URL + str(self.case_id) + "/?run=0"
        response = self.client.post(
            url,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(201, response.status_code)
        response = response.json

        row = self.model.query.get(response["id"])
        self.assertEqual(row.id, response["id"])
        self.assertTrue(row.config.get("checks_and_kpis_only"))
        self.assertTrue(row.checks_and_kpis_only)

        response = self.client.get(
            EXECUTION_URL,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 0)

        response = self.client.get(
            f"{EXECUTION_URL}?checks_and_kpis=true",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)

    @patch("cornflow.endpoints.data_check.Airflow")
    def test_new_data_check_execution_run(self, af_client_class):
        """
        Test case data check with Airflow integration.

        Verifies:

        - Successful data check creation
        - Airflow client interaction
        - Configuration validation
        - Response structure
        """
        patch_af_client(af_client_class)

        url = DATA_CHECK_CASE_URL + str(self.case_id) + "/"
        response = self.client.post(
            url,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(201, response.status_code)
        response = response.json

        row = self.model.query.get(response["id"])
        self.assertEqual(row.id, response["id"])
        self.assertTrue(row.config.get("checks_and_kpis_only"))
        self.assertTrue(row.checks_and_kpis_only)


def patch_pulse_client(pulse_client_class, alive=True, run_id="pulse-run-1"):
    """Pulse.from_config returns a mock: alive, and run_workflow answers with run_id."""
    pulse_client = pulse_client_class.from_config.return_value
    pulse_client.is_alive.return_value = alive
    pulse_client.run_workflow.return_value.json.return_value = {"run_id": run_id}
    return pulse_client


class TestDataChecksPulse(CustomTestCase):
    """
    Data check endpoints with the Pulse backend (CORNFLOW_BACKEND=3): the checks
    are launched in Pulse (checks_and_kpis_only), never in Airflow.
    """

    def setUp(self):
        super().setUp()
        current_app.config["CORNFLOW_BACKEND"] = PULSE_BACKEND
        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        self.instance_id = self.create_new_row(INSTANCE_URL, InstanceModel, payload)
        self.model = ExecutionModel

    def post_check(self, url):
        return self.client.post(
            url, follow_redirects=True, headers=self.get_header_with_auth(self.token)
        )

    def assert_queued_in_pulse(self, response, pulse_client, schema, case_id=None):
        self.assertEqual(201, response.status_code)
        row = self.model.query.get(response.json["id"])
        self.assertEqual("pulse-run-1", row.run_id)
        self.assertEqual(EXEC_STATE_QUEUED, row.state)
        # Set on every data check, also when an existing execution is checked
        # (checks_and_kpis_only is only set on the executions cornflow creates for it)
        self.assertTrue(row.last_run_checks_and_kpis)
        pulse_client.run_workflow.assert_called_once_with(
            row.id, workflow_name=schema, checks_and_kpis_only=True, case_id=case_id
        )

    @patch("cornflow.endpoints.data_check.Airflow")
    @patch("cornflow.endpoints.data_check.Pulse")
    def test_instance_check_runs_in_pulse(self, pulse_client_class, af_client_class):
        pulse_client = patch_pulse_client(pulse_client_class)
        response = self.post_check(DATA_CHECK_INSTANCE_URL + self.instance_id + "/")
        instance = InstanceModel.query.get(self.instance_id)
        self.assert_queued_in_pulse(response, pulse_client, instance.schema)
        self.assertTrue(self.model.query.get(response.json["id"]).checks_and_kpis_only)
        af_client_class.from_config.assert_not_called()

    @patch("cornflow.endpoints.data_check.Airflow")
    @patch("cornflow.endpoints.data_check.Pulse")
    def test_execution_check_runs_in_pulse(self, pulse_client_class, af_client_class):
        pulse_client = patch_pulse_client(pulse_client_class)
        with open(EXECUTION_PATH) as f:
            payload = json.load(f)
        payload["instance_id"] = self.instance_id
        exec_id = self.create_new_row(EXECUTION_URL_NORUN, self.model, payload=payload)

        response = self.post_check(DATA_CHECK_EXECUTION_URL + exec_id + "/")

        self.assertEqual(exec_id, response.json["id"])
        execution = ExecutionModel.query.get(exec_id)
        self.assert_queued_in_pulse(response, pulse_client, execution.schema)
        af_client_class.from_config.assert_not_called()

    @patch("cornflow.endpoints.data_check.Airflow")
    @patch("cornflow.endpoints.data_check.Pulse")
    def test_case_check_runs_in_pulse(self, pulse_client_class, af_client_class):
        pulse_client = patch_pulse_client(pulse_client_class)
        with open(CASE_PATH) as f:
            payload = json.load(f)
        case_id = self.create_new_row(CASE_URL, CaseModel, payload)

        response = self.post_check(DATA_CHECK_CASE_URL + str(case_id) + "/")

        case = CaseModel.query.get(case_id)
        self.assert_queued_in_pulse(
            response, pulse_client, case.schema or "solve_model_dag", case_id=case_id
        )
        af_client_class.from_config.assert_not_called()

    @patch("cornflow.endpoints.data_check.Pulse")
    def test_pulse_not_reachable(self, pulse_client_class):
        pulse_client = patch_pulse_client(pulse_client_class, alive=False)

        response = self.post_check(DATA_CHECK_INSTANCE_URL + self.instance_id + "/")

        self.assertEqual(400, response.status_code)
        self.assertEqual("Pulse is not accessible", response.json["error"])
        pulse_client.run_workflow.assert_not_called()
        row = self.model.query.filter_by(instance_id=self.instance_id).one()
        self.assertEqual(EXEC_STATE_ERROR_START, row.state)
