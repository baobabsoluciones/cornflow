from cornflow.tests.custom_test_case import CustomTestCase
from cornflow.models import ExecutionModel, InstanceModel
from cornflow.tests.custom_liveServer import CustomTestCaseLive

INSTANCE_PATH = './cornflow/tests/data/new_instance.json'
EXECUTION_PATH = './cornflow/tests/data/new_execution.json'
EXECUTIONS_LIST = [EXECUTION_PATH, './cornflow/tests/data/new_execution_2.json']


class TestExecutionAirflow(CustomTestCaseLive):

    def setUp(self):
        super().setUp()
        self.url = None
        self.model = None
