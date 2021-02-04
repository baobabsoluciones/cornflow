from cornflow.tests.custom_liveServer import CustomTestCaseLive

INSTANCE_PATH = './cornflow/tests/data/new_instance.json'
EXECUTION_PATH = './cornflow/tests/data/new_execution.json'
EXECUTIONS_LIST = [EXECUTION_PATH, './cornflow/tests/data/new_execution_2.json']


class TestExecutionAirflow(CustomTestCaseLive):

    def setUp(self, create_all=False):
        super().setUp(create_all=create_all)
        self.url = None
        self.model = None
