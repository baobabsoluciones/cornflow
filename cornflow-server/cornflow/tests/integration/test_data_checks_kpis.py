# Imports from internal modules
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.shared import db
from cornflow.shared.const import EXEC_STATE_STOPPED
from cornflow.tests.custom_liveServer import CustomTestCaseLive
from cornflow.tests.const import (
    INSTANCE_PATH_1_ROSTERING,
    SOLUTION_PATH_1_ROSTERING,
    INSTANCE_PATH_2_ROSTERING,
    INSTANCE_PATH_3_ROSTERING,
    SOLUTION_PATH_3_ROSTERING,
    INSTANCE_PATH_4_ROSTERING,
    SOLUTION_PATH_4_ROSTERING,
    DATA_CHECK_INSTANCE_URL,
    DATA_CHECK_EXECUTION_URL,
    DATA_CHECK_CASE_URL,
)

# Imports from external libraries
from flask import current_app
import json
import os
import time


def load_file(_file):
    with open(_file) as f:
        temp = json.load(f)
    return temp


class TestDataChecks(CustomTestCaseLive):
    """
    Test case for checking the data checks dag and the associated workflows.
    """

    @classmethod
    def setUpClass(cls):
        app = cls.create_app(cls)
        with app.app_context():
            db.create_all()
            access_init_command(False)
            config = current_app.config
            register_deployed_dags_command(
                config["AIRFLOW_URL"],
                config["AIRFLOW_USER"],
                config["AIRFLOW_PWD"],
                False,
            )

        cls.instance_url = DATA_CHECK_INSTANCE_URL
        cls.execution_url = DATA_CHECK_EXECUTION_URL
        cls.case_url = DATA_CHECK_CASE_URL

        # Instance data-solution with an error in the solution checks
        cls.instance_data_1 = load_file(INSTANCE_PATH_1_ROSTERING)
        cls.solution_data_1 = load_file(SOLUTION_PATH_1_ROSTERING)
        # Instance with an error in the instance checks
        cls.instance_data_2 = load_file(INSTANCE_PATH_2_ROSTERING)
        # Instance data-solution without errors in the solution data checks
        cls.instance_data_3 = load_file(INSTANCE_PATH_3_ROSTERING)
        cls.solution_data_3 = load_file(SOLUTION_PATH_3_ROSTERING)
        # Instance data-solution with only one employee
        cls.instance_data_4 = load_file(INSTANCE_PATH_4_ROSTERING)
        cls.solution_data_4 = load_file(SOLUTION_PATH_4_ROSTERING)

    @classmethod
    def tearDownClass(cls):
        app = cls.create_app(cls)
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def setUp(self):
        user_data = dict(
            username="testname",
            email="test@test.com",
            pwd="Testpassword1!",
        )
        self.set_client(self.get_server_url())
        response = self.login_or_signup(user_data)
        self.client.token = response["token"]
        register_dag_permissions_command(
            open_deployment=current_app.config["OPEN_DEPLOYMENT"], verbose=False
        )
        os.environ["CORNFLOW_SERVICE_USER"] = "service_user"

        self.create_service_user(
            dict(username="airflow", pwd="Airflow_test_password1", email="af@cf.com")
        )

    def tearDown(self):
        pass

    def test_data_checks_correct_instance(self):
        """
        Launches data checks on an instance. Checks that the execution is created
        correctly, that we can access its status, and that the results are saved correctly.
        """
        # Create an instance
        instance = self.client.create_instance(
            name="Test instance", schema="rostering", data=self.instance_data_1
        )
        instance_id = instance["id"]

        # Create data checks on an instance
        execution = self.client.create_instance_data_check(instance_id)
        self.assertIn("id", execution)
        execution_id = execution["id"]

        # Checks that we can access the execution status and that
        # the execution finishes correctly
        status = 0
        while status in [0, -7]:
            time.sleep(0.5)
            response = self.client.get_status(execution_id)
            self.assertIn("state", response)
            status = response["state"]

        self.assertEqual(status, 1)
        time.sleep(1)

        # Checks that the results of the data checks are saved
        #   correctly in the instance
        data = self.client.get_one_instance_data(instance_id)
        self.assertIn("checks", data)
        self.assertEqual(data["checks"], {})

    def test_data_checks_incorrect_instance(self):
        """
        Launches data checks on an instance with errors in the instance data.
        Checks that the execution is created correctly, that we can access its
        status, and that the results are saved correctly.
        """
        # Create an instance
        instance = self.client.create_instance(
            name="Test instance", schema="rostering", data=self.instance_data_2
        )
        instance_id = instance["id"]

        # Create data checks on an instance
        execution = self.client.create_instance_data_check(instance_id)
        self.assertIn("id", execution)
        execution_id = execution["id"]

        # Checks that we can access the execution status and that
        # the execution finishes correctly
        status = 0
        while status in [0, -7]:
            time.sleep(0.5)
            response = self.client.get_status(execution_id)
            self.assertIn("state", response)
            status = response["state"]

        self.assertEqual(status, 1)
        time.sleep(1)

        # Checks that the results of the data checks are saved
        #   correctly in the instance
        data = self.client.get_one_instance_data(instance_id)
        self.assertIn("checks", data)
        self.assertIsInstance(data["checks"], dict)
        self.assertNotEqual(len(data["checks"]), 0)
        self.assertIn("timeslot_length", data["checks"])

    def test_data_checks_kpis_correct_execution(self):
        """
        Launches data checks and kpis on a solution with correct data.
        Checks that the execution is created correctly, that we can access
        its status, and that the results are saved correctly.
        """
        # Create an instance
        instance = self.client.create_instance(
            name="Test instance", schema="rostering", data=self.instance_data_3
        )
        instance_id = instance["id"]

        # Create an execution with the solution
        api = "execution/?run=0"
        payload = dict(
            config={},
            instance_id=instance_id,
            name="Test execution",
            schema="rostering",
            data=self.solution_data_3,
        )
        response = self.client.raw.create_api(api, json=payload, encoding="br")
        execution_id = response.json()["id"]

        # Create data checks and kpis on a solution
        execution = self.client.create_execution_data_check_kpis(execution_id)
        self.assertIn("id", execution)
        self.assertEqual(execution["id"], execution_id)

        # Checks that we can access the execution status and that
        # the execution finishes correctly
        status = 0
        while status in [0, -7]:
            time.sleep(0.5)
            response = self.client.get_status(execution_id)
            self.assertIn("state", response)
            status = response["state"]

        self.assertEqual(status, 1)
        time.sleep(1)

        # Checks that the results of the data checks and kpis are saved
        #   correctly in the instance and in the solution
        data = self.client.get_one_instance_data(instance_id)
        self.assertIn("checks", data)
        self.assertEqual(data["checks"], {})
        solution_data = self.client.get_solution(execution_id)
        self.assertIn("checks", solution_data)
        self.assertEqual(solution_data["checks"], {})
        self.assertIn("kpis", solution_data)
        self.assertIn("globals", solution_data["kpis"])
        self.assertNotEqual(len(solution_data["kpis"]["globals"]), 0)
        self.assertIn("mean_demand_per_employee", solution_data["kpis"])
        self.assertNotEqual(len(solution_data["kpis"]["mean_demand_per_employee"]), 0)

    def test_data_checks_kpis_incorrect_execution_1(self):
        """
        Launches data checks and kpis on a solution with incorrect instance
        and solution data.
        Checks that the execution is created correctly, that we can access
        its status, and that the results are saved correctly.
        """
        # Create an instance
        instance = self.client.create_instance(
            name="Test instance", schema="rostering", data=self.instance_data_2
        )
        instance_id = instance["id"]

        # Create an execution with the solution
        api = "execution/?run=0"
        payload = dict(
            config={},
            instance_id=instance_id,
            name="Test execution",
            schema="rostering",
            data=self.solution_data_3,
        )
        response = self.client.raw.create_api(api, json=payload, encoding="br")
        execution_id = response.json()["id"]

        # Create data checks and kpis on a solution
        execution = self.client.create_execution_data_check_kpis(execution_id)
        self.assertIn("id", execution)
        self.assertEqual(execution["id"], execution_id)

        # Checks that we can access the execution status and that
        # the execution finishes correctly
        status = 0
        while status in [0, -7]:
            time.sleep(0.5)
            response = self.client.get_status(execution_id)
            self.assertIn("state", response)
            status = response["state"]

        self.assertEqual(status, 1)
        time.sleep(1)

        # Checks that the results of the data checks are saved
        #   correctly in the instance.
        data = self.client.get_one_instance_data(instance_id)
        self.assertIn("checks", data)
        self.assertIsInstance(data["checks"], dict)
        self.assertNotEqual(len(data["checks"]), 0)
        self.assertIn("timeslot_length", data["checks"])
        solution_data = self.client.get_solution(execution_id)
        self.assertIn("checks", solution_data)
        self.assertIsInstance(solution_data["checks"], dict)
        self.assertNotEqual(len(solution_data["checks"]), 0)
        self.assertIn("kpis", solution_data)
        self.assertIsNone(solution_data["kpis"])

    def test_data_checks_kpis_incorrect_execution_2(self):
        """
        Launches data checks and kpis on a solution with incorrect solution data.
        Checks that the execution is created correctly, that we can access
        its status, and that the results are saved correctly.
        """
        # Create an instance
        instance = self.client.create_instance(
            name="Test instance", schema="rostering", data=self.instance_data_1
        )
        instance_id = instance["id"]

        # Create an execution with the solution
        api = "execution/?run=0"
        payload = dict(
            config={},
            instance_id=instance_id,
            name="Test execution",
            schema="rostering",
            data=self.solution_data_1,
        )
        response = self.client.raw.create_api(api, json=payload, encoding="br")
        execution_id = response.json()["id"]

        # Create data checks and kpis on a solution
        execution = self.client.create_execution_data_check_kpis(execution_id)
        self.assertIn("id", execution)
        self.assertEqual(execution["id"], execution_id)

        # Checks that we can access the execution status and that
        # the execution finishes correctly
        status = 0
        while status in [0, -7]:
            time.sleep(0.5)
            response = self.client.get_status(execution_id)
            self.assertIn("state", response)
            status = response["state"]

        self.assertEqual(status, 1)
        time.sleep(1)

        # Checks that the results of the data checks are saved
        #   correctly in the solution. Instance checks should not have results.
        data = self.client.get_one_instance_data(instance_id)
        self.assertIn("checks", data)
        self.assertEqual(data["checks"], {})
        solution_data = self.client.get_solution(execution_id)
        self.assertIn("checks", solution_data)
        self.assertIsInstance(solution_data["checks"], dict)
        self.assertNotEqual(len(solution_data["checks"]), 0)
        self.assertIn("days_worked_per_week", solution_data["checks"])
        self.assertNotEqual(len(solution_data["checks"]["days_worked_per_week"]), 0)
        self.assertIn("kpis", solution_data)
        self.assertIsNone(solution_data["kpis"])

    def test_data_checks_kpis_errors_kpis_check(self):
        """
        Launches data checks and kpis on an execution in which the check_kpis method
        will return an error.
        """
        # Create an instance
        instance = self.client.create_instance(
            name="Test instance", schema="rostering", data=self.instance_data_4
        )
        instance_id = instance["id"]

        # Create an execution with the solution
        api = "execution/?run=0"
        payload = dict(
            config={},
            instance_id=instance_id,
            name="Test execution",
            schema="rostering",
            data=self.solution_data_4,
        )
        response = self.client.raw.create_api(api, json=payload, encoding="br")
        execution_id = response.json()["id"]

        # Create data checks and kpis on a solution
        execution = self.client.create_execution_data_check_kpis(execution_id)
        self.assertIn("id", execution)
        self.assertEqual(execution["id"], execution_id)

        # Checks that we can access the execution status and that
        # the execution finishes correctly
        status = 0
        while status in [0, -7]:
            time.sleep(0.5)
            response = self.client.get_status(execution_id)
            self.assertIn("state", response)
            status = response["state"]

        self.assertEqual(status, 1)
        time.sleep(1)

        # Checks that the results of the data checks, kpis and kpis checks are
        #   correctly saved.
        data = self.client.get_one_instance_data(instance_id)
        self.assertIn("checks", data)
        self.assertEqual(data["checks"], {})
        solution_data = self.client.get_solution(execution_id)
        self.assertIn("checks", solution_data)
        self.assertIsInstance(solution_data["checks"], dict)
        self.assertNotEqual(len(solution_data["checks"]), 0)
        self.assertIn("only_one_employee_percentage", solution_data["checks"])
        self.assertIn(
            "percentage", solution_data["checks"]["only_one_employee_percentage"]
        )
        self.assertIn("kpis", solution_data)
        self.assertIsInstance(solution_data["kpis"], dict)
        self.assertIn("globals", solution_data["kpis"])
        self.assertNotEqual(len(solution_data["kpis"]["globals"]), 0)
        self.assertIn("mean_demand_per_employee", solution_data["kpis"])
        self.assertNotEqual(len(solution_data["kpis"]["mean_demand_per_employee"]), 0)

    def test_data_checks_kpis_correct_case(self):
        """
        Launches data checks and kpis on a case with correct data.
        Checks that the execution is created correctly, that we can access
        its status, and that the results are saved correctly.
        """
        # Create a case with a solution
        response = self.client.create_case(
            name="Test case",
            schema="rostering",
            data=self.instance_data_3,
            solution=self.solution_data_3,
        )
        case_id = response["id"]

        # Create data checks and kpis on a solution
        execution = self.client.create_case_data_check_kpis(case_id)
        self.assertIn("id", execution)
        execution_id = execution["id"]

        # Checks that we can access the execution status and that
        # the execution finishes correctly
        status = 0
        while status in [0, -7]:
            time.sleep(0.5)
            response = self.client.get_status(execution_id)
            self.assertIn("state", response)
            status = response["state"]

        self.assertEqual(status, 1)
        time.sleep(1)

        # Checks that the results of the data checks and kpis are saved
        #   correctly in the instance and in the solution
        data = self.client.get_one_case_data(case_id)
        self.assertIn("checks", data)
        self.assertEqual(data["checks"], {})
        self.assertIn("solution_checks", data)
        self.assertEqual(data["solution_checks"], {})
        self.assertIn("kpis", data)
        self.assertIn("globals", data["kpis"])
        self.assertNotEqual(len(data["kpis"]["globals"]), 0)
        self.assertIn("mean_demand_per_employee", data["kpis"])
        self.assertNotEqual(len(data["kpis"]["mean_demand_per_employee"]), 0)

    def test_data_checks_kpis_incorrect_case(self):
        """
        Launches data checks and kpis on a case with incorrect instance and solution data.
        Checks that the execution is created correctly, that we can access
        its status, and that the results are saved correctly.
        """
        # Create a case with a solution
        response = self.client.create_case(
            name="Test case",
            schema="rostering",
            data=self.instance_data_2,
            solution=self.solution_data_1,
        )
        case_id = response["id"]

        # Create data checks and kpis on a solution
        execution = self.client.create_case_data_check_kpis(case_id)
        self.assertIn("id", execution)
        execution_id = execution["id"]

        # Checks that we can access the execution status and that
        # the execution finishes correctly
        status = 0
        while status in [0, -7]:
            time.sleep(0.5)
            response = self.client.get_status(execution_id)
            self.assertIn("state", response)
            status = response["state"]

        self.assertEqual(status, 1)
        time.sleep(1)

        # Checks that the results of the data checks are saved
        #   correctly in the instance and in the solution.
        data = self.client.get_one_case_data(case_id)
        self.assertIn("checks", data)
        self.assertIsInstance(data["checks"], dict)
        self.assertNotEqual(len(data["checks"]), 0)
        self.assertIn("timeslot_length", data["checks"])
        self.assertIn("solution_checks", data)
        self.assertIsInstance(data["solution_checks"], dict)
        self.assertNotEqual(len(data["solution_checks"]), 0)
        self.assertIn("days_worked_per_week", data["solution_checks"])
        self.assertNotEqual(len(data["solution_checks"]["days_worked_per_week"]), 0)
        self.assertIn("kpis", data)
        self.assertIsNone(data["kpis"])

    def test_stop_data_checks_execution(self):
        """
        Launches data checks on an execution and stops the execution.
        """
        # Create an instance
        instance = self.client.create_instance(
            name="Test instance", schema="rostering", data=self.instance_data_1
        )
        instance_id = instance["id"]

        # Create an execution with the solution
        api = "execution/?run=0"
        payload = dict(
            config={},
            instance_id=instance_id,
            name="Test execution",
            schema="rostering",
            data=self.solution_data_3,
        )
        response = self.client.raw.create_api(api, json=payload, encoding="br")
        execution_id = response.json()["id"]

        # Create data checks and kpis on a solution
        execution = self.client.create_execution_data_check_kpis(execution_id)
        self.assertIn("id", execution)
        self.assertEqual(execution["id"], execution_id)

        # Stop the execution
        response = self.client.stop_execution(execution_id)
        time.sleep(2)
        status = self.client.get_status(execution["id"])
        results = self.client.get_results(execution["id"])
        self.assertEqual(status["state"], EXEC_STATE_STOPPED)
        self.assertEqual(results["state"], EXEC_STATE_STOPPED)

    def test_relaunch_data_checks_execution(self):
        """
        Create an execution with correct data, launch data checks and kpis, relaunch the
        execution, wait for results.
        """
        # Create an instance
        instance = self.client.create_instance(
            name="Test instance", schema="rostering", data=self.instance_data_1
        )
        instance_id = instance["id"]

        # Create an execution with the solution
        api = "execution/?run=0"
        payload = dict(
            config={},
            instance_id=instance_id,
            name="Test execution",
            schema="rostering",
            data=self.solution_data_3,
        )
        response = self.client.raw.create_api(api, json=payload, encoding="br")
        execution_id = response.json()["id"]

        # Create data checks and kpis on a solution
        execution = self.client.create_execution_data_check_kpis(execution_id)
        self.assertIn("id", execution)
        self.assertEqual(execution["id"], execution_id)

        # Checks that we can access the execution status and that
        # the execution finishes correctly
        status = 0
        while status in [0, -7]:
            time.sleep(0.5)
            response = self.client.get_status(execution_id)
            self.assertIn("state", response)
            status = response["state"]

        self.assertEqual(status, 1)
        time.sleep(1)

        # Relaunch the execution (solving it)
        response = self.client.relaunch_execution(
            execution_id, config={"solver": "mip.PULP_CBC_CMD"}
        )

        # Checks that we can access the execution status and that
        # the execution finishes correctly
        status = 0
        while status in [0, -7]:
            time.sleep(0.5)
            response = self.client.get_status(execution_id)
            self.assertIn("state", response)
            status = response["state"]

        self.assertEqual(status, 1)

    def test_full_workflow(self):
        """
        Launch an execution, solve, edit solution, launch data checks and kpis,
        relaunch execution and stop it, relaunch data checks and stop them.
        Check that we can access the execution status at each step.
        """
        # Create an instance
        instance = self.client.create_instance(
            name="Test instance", schema="rostering", data=self.instance_data_3
        )
        instance_id = instance["id"]

        # Create an execution with the solution
        response = self.client.create_execution(
            instance_id=instance_id,
            name="Test execution",
            schema="rostering",
            config={"solver": "mip.PULP_CBC_CMD"},
        )
        execution_id = response["id"]

        # Checks that we can access the execution status and that
        # the execution finishes correctly
        status = 0
        while status in [0, -7]:
            time.sleep(0.5)
            response = self.client.get_status(execution_id)
            self.assertIn("state", response)
            status = response["state"]

        self.assertEqual(status, 1)
        time.sleep(1)

        # Edit the solution (add an employee with no assigned shifts)
        solution_data = self.client.get_solution(execution_id)
        self.assertIn("data", solution_data)
        self.assertIn("works", solution_data["data"])
        solution_data["data"]["works"][0]["timeslot"] = "2026-09-06T08:00"
        response = self.client.put_one_execution(
            execution_id, payload={"data": solution_data["data"]}
        )

        # Create data checks and kpis on a solution
        execution = self.client.create_execution_data_check_kpis(execution_id)
        self.assertIn("id", execution)
        self.assertEqual(execution["id"], execution_id)

        # Checks that we can access the execution status and that
        # the execution finishes correctly
        status = 0
        while status in [0, -7]:
            time.sleep(0.5)
            response = self.client.get_status(execution_id)
            self.assertIn("state", response)
            status = response["state"]

        self.assertEqual(status, 1)
        time.sleep(1)

        # Relaunch the execution (solving it)
        response = self.client.relaunch_execution(
            execution_id, config={"solver": "mip.PULP_CBC_CMD"}
        )

        # Checks that we can access the execution status and that
        # the execution is running
        response = self.client.get_status(execution_id)
        self.assertIn("state", response)
        status = response["state"]
        self.assertIn(status, [0, -7])

        # Stop the execution
        response = self.client.stop_execution(execution_id)
        time.sleep(1)
        status = self.client.get_status(execution_id)
        self.assertEqual(status["state"], EXEC_STATE_STOPPED)

        # Relaunch data checks
        execution = self.client.create_execution_data_check_kpis(execution_id)
        self.assertIn("id", execution)
        self.assertEqual(execution["id"], execution_id)

        # Checks that we can access the execution status and that
        # the execution is running correctly
        response = self.client.get_status(execution_id)
        self.assertIn("state", response)
        status = response["state"]
        self.assertIn(status, [0, -7])

        # Stop the execution
        response = self.client.stop_execution(execution_id)
        time.sleep(1)
        status = self.client.get_status(execution["id"])
        self.assertEqual(status["state"], EXEC_STATE_STOPPED)
