from cornflow.models import ExecutionModel, InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase, BaseTestCases
import json
from cornflow.tests.const import (
    INSTANCE_PATH,
    DAG_URL,
    EXECUTION_URL_NORUN,
    CASE_PATH,
    INSTANCE_URL,
)
from cornflow.shared.const import EXEC_STATE_CORRECT
from cornflow.tests.unit.test_executions import TestExecutionsDetailEndpointMock


# TODO: this test should pass but fails
class TestDagEndpoint(TestExecutionsDetailEndpointMock):
    def test_manual_dag(self):
        with open(CASE_PATH) as f:
            payload = json.load(f)
        data = dict(
            data=payload["data"],
            state=EXEC_STATE_CORRECT,
        )
        payload_to_send = {**self.payload, **data}
        token = self.create_service_user()
        # idx = self.create_new_row(
        #     url=DAG_URL,
        #     model=self.model,
        #     payload=payload_to_send,
        #     check_payload=False,
        #     token=token,
        # )
        # print(idx)


class TestDagDetailEndpoint(TestExecutionsDetailEndpointMock):
    def test_put_dag(self):
        idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
        with open(CASE_PATH) as f:
            payload = json.load(f)
        data = dict(
            data=payload["data"],
            state=EXEC_STATE_CORRECT,
        )
        payload_to_check = {**self.payload, **data}
        token = self.create_service_user()
        data = self.update_row(
            url=DAG_URL + idx + "/",
            payload_to_check=payload_to_check,
            change=data,
            token=token,
            check_payload=False,
        )

    def test_get_dag(self):
        idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
        token = self.create_service_user()
        data = self.get_one_row(
            url=DAG_URL + idx + "/",
            token=token,
            check_payload=False,
            payload=self.payload,
        )
        instance_data = self.get_one_row(
            url=INSTANCE_URL + self.payload["instance_id"] + "/data/",
            payload=dict(),
            check_payload=False,
        )
        self.assertEqual(data["data"], instance_data["data"])
        self.assertEqual(data["config"], self.payload["config"])
        return
