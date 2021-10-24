import json
import pulp
import logging as log
import time
import unittest

from cornflow_client import CornFlowApiError
from cornflow_client.constants import INSTANCE_SCHEMA, SOLUTION_SCHEMA

from cornflow.tests.custom_liveServer import CustomTestCaseLive
from cornflow.shared.const import (
    EXEC_STATE_CORRECT,
    EXEC_STATE_STOPPED,
    EXEC_STATE_RUNNING,
)
from cornflow.tests.const import INSTANCE_PATH
from cornflow.shared.const import STATUS_HEALTHY
from cornflow.schemas.solution_log import LogSchema
from airflow_config.dags.model_functions import solve as solve_model


def load_file(_file):
    with open(_file) as f:
        temp = json.load(f)
    return temp


class TestCornflowClientBasic(CustomTestCaseLive):
    def setUp(self, create_all=False):
        super().setUp()
        self.items_to_check = ["name", "description"]

    def create_new_instance_file(self, mps_file):
        name = "test_instance1"
        description = "description123"
        response = self.client.create_instance_file(
            filename=mps_file, name=name, description=description, minimize=True
        )
        self.assertTrue("id" in response)
        instance = self.client.get_one_instance(response["id"])
        log.debug("Got instance with id: {}".format(instance["id"]))
        # row = InstanceModel.query.get(response['id'])
        self.assertEqual(instance["id"], response["id"])
        self.assertEqual(instance["name"], name)
        self.assertEqual(instance["description"], description)
        payload = pulp.LpProblem.fromMPS(mps_file, sense=1)[1].toDict()
        instance_data = self.client.get_api_for_id(
            "instance", response["id"], "data"
        ).json()
        self.assertEqual(instance_data["data"], payload)
        log.debug("validated instance data")
        return instance

    def create_new_instance(self, mps_file):
        name = "test_instance1"
        description = "description123"
        data = pulp.LpProblem.fromMPS(mps_file, sense=1)[1].toDict()
        schema = "solve_model_dag"
        payload = dict(data=data, name=name, description=description)
        return self.create_new_instance_payload(payload)

    def create_new_instance_payload(self, payload):
        response = self.client.create_instance(**payload)
        log.debug("Created instance with id: {}".format(response["id"]))
        self.assertTrue("id" in response)
        instance = self.client.get_one_instance(response["id"])
        log.debug("Instance with id={} exists in server".format(instance["id"]))
        self.assertEqual(instance["id"], response["id"])
        self.assertEqual(instance["name"], payload["name"])
        self.assertEqual(instance["description"], payload["description"])
        instance_data = self.client.get_api_for_id(
            "instance", response["id"], "data"
        ).json()
        self.assertEqual(instance_data["data"], payload["data"])
        return instance

    def create_new_case_payload(self, payload):
        response = self.client.create_case(**payload)
        self.assertTrue("id" in response)
        log.debug("Created case with id: {}".format(response["id"]))
        case = self.client.get_one_case(response["id"])
        log.debug("Case with id={} exists in server".format(case["id"]))
        self.assertEqual(case["id"], response["id"])
        self.assertEqual(case["name"], payload["name"])
        self.assertEqual(case["description"], payload["description"])
        case_data = self.client.get_api_for_id("case", response["id"], "data").json()
        self.assertEqual(case_data["data"], payload["data"])
        return case

    def create_new_execution(self, payload):
        response = self.client.create_execution(**payload)
        log.debug("Created execution with id={}".format(response["id"]))
        self.assertTrue("id" in response)
        execution = self.client.get_results(response["id"])
        log.debug("Execution with id={} exists in server".format(execution["id"]))
        self.assertEqual(execution["id"], response["id"])
        for item in self.items_to_check:
            self.assertEqual(execution[item], payload[item])
        response = self.client.get_status(response["id"])
        self.assertTrue("state" in response)
        log.debug("Execution has state={} in server".format(response["state"]))
        return execution

    def create_instance_and_execution(self):
        one_instance = self.create_new_instance("./cornflow/tests/data/test_mps.mps")
        name = "test_execution_name_123"
        description = "test_execution_description_123"
        schema = "solve_model_dag"
        payload = dict(
            instance_id=one_instance["id"],
            config=dict(solver="PULP_CBC_CMD", timeLimit=10),
            description=description,
            name=name,
            schema=schema,
        )
        return self.create_new_execution(payload)

    def create_timer_instance_and_execution(self, seconds=5):
        payload = dict(
            data=dict(seconds=seconds),
            name="timer_instance",
            schema="timer",
            description="timer_description",
        )
        one_instance = self.create_new_instance_payload(payload)
        payload = dict(
            instance_id=one_instance["id"],
            config=dict(),
            name="timer_execution",
            description="timer_exec_description",
            schema="timer",
        )
        return self.create_new_execution(payload)


class TestCornflowClient(TestCornflowClientBasic):

    # TODO: user management
    # TODO: infeasible execution

    def test_new_instance_file(self):
        self.create_new_instance_file("./cornflow/tests/data/test_mps.mps")

    def test_new_instance(self):
        return self.create_new_instance("./cornflow/tests/data/test_mps.mps")

    def test_get_instance__data(self):
        instance = self.create_new_instance("./cornflow/tests/data/test_mps.mps")
        response = self.client.get_api_for_id("instance", instance["id"], "data")
        self.assertEqual(response.headers["Content-Encoding"], "gzip")

    def test_delete_instance(self):
        instance = self.test_new_instance()
        response = self.client.get_api_for_id("instance", instance["id"])
        self.assertEqual(200, response.status_code)
        response = self.client.delete_api_for_id("instance", instance["id"])
        self.assertEqual(200, response.status_code)
        response = self.client.get_api_for_id("instance", instance["id"])
        self.assertEqual(404, response.status_code)

    def test_new_execution(self):
        return self.create_instance_and_execution()

    def test_delete_execution(self):
        execution = self.test_new_execution()
        response = self.client.get_api_for_id("execution/", execution["id"])
        self.assertEqual(200, response.status_code)
        response = self.client.delete_api_for_id("execution/", execution["id"])
        self.assertEqual(200, response.status_code)
        response = self.client.get_api_for_id("execution/", execution["id"])
        self.assertEqual(404, response.status_code)

    def test_get_dag_schema_good(self):
        response = self.client.get_schema("solve_model_dag")
        for sch in [INSTANCE_SCHEMA, SOLUTION_SCHEMA]:
            content = response[sch]
            self.assertTrue("properties" in content)

    def test_get_all_schemas(self):
        response = self.client.get_all_schemas()
        self.assertIn({"name": "solve_model_dag"}, response)

    def test_get_dag_schema_no_schema(self):
        response = self.client.get_schema("this_dag_does_not_exist")
        self.assertTrue("error" in response)

    def test_new_execution_bad_dag_name(self):
        one_instance = self.create_new_instance("./cornflow/tests/data/test_mps.mps")
        name = "test_execution_name_123"
        description = "test_execution_description_123"
        payload = dict(
            instance_id=one_instance["id"],
            config=dict(solver="PULP_CBC_CMD", timeLimit=10),
            description=description,
            name=name,
            schema="solve_model_dag_bad_this_does_not_exist",
        )
        _bad_func = lambda: self.client.create_execution(**payload)
        self.assertRaises(CornFlowApiError, _bad_func)

    def test_new_execution_with_schema(self):
        one_instance = self.create_new_instance("./cornflow/tests/data/test_mps.mps")
        name = "test_execution_name_123"
        description = "test_execution_description_123"
        payload = dict(
            instance_id=one_instance["id"],
            config=dict(solver="PULP_CBC_CMD", timeLimit=10),
            description=description,
            name=name,
            schema="solve_model_dag",
        )
        return self.create_new_execution(payload)

    def test_new_instance_with_default_schema_bad(self):
        payload = load_file(INSTANCE_PATH)
        payload["data"].pop("objective")
        _error_fun = lambda: self.client.create_instance(**payload)
        self.assertRaises(CornFlowApiError, _error_fun)

    def test_new_instance_with_schema_bad(self):
        payload = load_file(INSTANCE_PATH)
        payload["data"].pop("objective")
        payload["schema"] = "solve_model_dag"
        _error_fun = lambda: self.client.create_instance(**payload)
        self.assertRaises(CornFlowApiError, _error_fun)

    def test_new_instance_with_schema_additional_data(self):
        payload = load_file(INSTANCE_PATH)
        payload["data"]["objective"]["inexistant_property"] = 1
        payload["schema"] = "solve_model_dag"
        self.client.create_instance(**payload)

    def test_new_instance_with_schema_good(self):

        payload = load_file(INSTANCE_PATH)
        payload["schema"] = "solve_model_dag"
        self.create_new_instance_payload(payload)

    def test_new_case_without_parent(self):
        payload = load_file(INSTANCE_PATH)
        self.create_new_case_payload(payload)

    def test_new_case_with_parent(self):
        payload = load_file(INSTANCE_PATH)
        payload_dir = dict(payload)
        payload_dir.pop("data")
        response = self.client.create_case(**payload_dir)
        payload["parent_id"] = response["id"]
        case2 = self.create_new_case_payload(payload)
        self.assertEqual(case2["path"], "{}/".format(response["id"]))

    def test_server_alive(self):
        data = self.client.is_alive()
        cf_status = data["cornflow_status"]
        af_status = data["airflow_status"]
        self.assertEqual(str, type(cf_status))
        self.assertEqual(str, type(af_status))
        self.assertEqual(cf_status, STATUS_HEALTHY)
        self.assertEqual(af_status, STATUS_HEALTHY)


# TODO: maybe we should have a test-suite for service_user


class TestCornflowClientAdmin(TestCornflowClientBasic):
    def setUp(self, create_all=False):
        super().setUp()

        # we create a service user:
        self.create_service_user(
            dict(username="airflow", pwd="airflow_test_password", email="af@cf.com")
        )
        # we create an admin user
        # we guarantee that the admin is there for airflow
        self.client.token = self.create_admin(
            dict(
                username="airflow_test@admin.com",
                email="airflow_test@admin.com",
                pwd="airflow_test_password",
            )
        )

    def test_solve_and_wait(self):
        execution = self.create_instance_and_execution()
        time.sleep(15)
        status = self.client.get_status(execution["id"])
        results = self.client.get_results(execution["id"])
        self.assertEqual(status["state"], EXEC_STATE_CORRECT)
        self.assertEqual(results["state"], EXEC_STATE_CORRECT)

    def test_interrupt(self):
        execution = self.create_timer_instance_and_execution(5)
        self.client.stop_execution(execution_id=execution["id"])
        time.sleep(2)
        status = self.client.get_status(execution["id"])
        results = self.client.get_results(execution["id"])
        self.assertEqual(status["state"], EXEC_STATE_STOPPED)
        self.assertEqual(results["state"], EXEC_STATE_STOPPED)

    def test_status_solving(self):
        execution = self.create_timer_instance_and_execution(5)
        status = self.client.get_status(execution["id"])
        self.assertEqual(status["state"], EXEC_STATE_RUNNING)

    def test_manual_execution(self):

        instance_payload = load_file(INSTANCE_PATH)
        one_instance = self.create_new_instance_payload(instance_payload)
        name = "test_execution_name_123"
        description = "test_execution_description_123"
        # for the solution we can use the same standard than the instance data
        payload = dict(
            instance_id=one_instance["id"],
            config=dict(solver="PULP_CBC_CMD", timeLimit=10),
            description=description,
            name=name,
            data=instance_payload["data"],
            schema="solve_model_dag",
        )
        response = self.client.manual_execution(**payload)
        execution = self.client.get_results(response["id"])
        self.assertEqual(execution["id"], response["id"])
        for item in ["config", "description", "name"]:
            self.assertEqual(execution[item], payload[item])
        response = self.client.get_status(response["id"])
        self.assertTrue("state" in response)
        execution_data = self.client.get_solution(response["id"])
        self.assertEqual(execution_data["data"], payload["data"])

    def test_manual_execution2(self):
        instance_payload = load_file(INSTANCE_PATH)
        one_instance = self.create_new_instance_payload(instance_payload)
        name = "test_execution_name_123"
        description = "test_execution_description_123"
        payload = dict(
            instance_id=one_instance["id"],
            config=dict(solver="PULP_CBC_CMD", timeLimit=10),
            description=description,
            name=name,
            schema="solve_model_dag",
        )
        response = self.client.manual_execution(**payload)
        execution = self.client.get_results(response["id"])
        self.assertEqual(execution["id"], response["id"])
        for item in ["config", "description", "name"]:
            self.assertEqual(execution[item], payload[item])
        response = self.client.get_status(response["id"])
        self.assertTrue("state" in response)
        execution_data = self.client.get_solution(response["id"])
        self.assertIsNone(execution_data["data"])

    def test_edit_one_execution(self):
        one_instance = self.create_new_instance("./cornflow/tests/data/test_mps.mps")
        payload = dict(
            name="bla", config=dict(solver="CBC"), instance_id=one_instance["id"]
        )
        execution = self.client.create_api("execution/?run=0", json=payload)
        payload = dict(log_text="")
        response = self.client.put_api_for_id(
            api="dag/", id=execution.json()["id"], payload=payload
        )
        self.assertEqual(response.status_code, 200)


class PuLPLogSchema(unittest.TestCase):
    def solve_model(self, input_data, config):
        return solve_model(input_data, config)

    def dump_progress(self, log_dict):
        LS = LogSchema()
        return LS.load(log_dict)

    def solve_test_progress(self):
        with open("./cornflow/tests/data/gc_20_7.json", "r") as f:
            data = json.load(f)

        config = dict(solver="PULP_CBC_CMD", timeLimit=10)
        solution, log, log_dict = self.solve_model(data, config)
        loaded_data = self.dump_progress(log_dict)
        self.assertEqual(loaded_data["solver"], "CBC")
        self.assertEqual(loaded_data["version"], "2.9.0")
        matrix_keys = {"nonzeros", "constraints", "variables"}
        a = matrix_keys.symmetric_difference(loaded_data["matrix"].keys())
        self.assertEqual(len(a), 0)

    def test_progress2(self):
        with open("./cornflow/tests/data/gc_50_3_log.json", "r") as f:
            data = json.load(f)
        loaded_data = self.dump_progress(data)
        self.assertEqual(loaded_data["solver"], "CPLEX")
        self.assertEqual(type(loaded_data["progress"]["Node"][0]), str)
        self.assertEqual(type(loaded_data["progress"]["Time"][0]), str)
        self.assertEqual(type(loaded_data["cut_info"]["cuts"]["Clique"]), int)
        self.assertEqual(type(loaded_data["nodes"]), int)
