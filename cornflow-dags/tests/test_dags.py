import os, sys
prev_dir = os.path.join(os.path.dirname(__file__), "../DAG")
sys.path.insert(1, prev_dir)
import unittest
from update_all_schemas import get_all_apps
from cornflow_client import SchemaManager


class TestLoaderWithKwargs(unittest.TestLoader):
    """A test loader which allows to parse keyword arguments to the
       test case class."""
    def loadTestsFromTestCase(self, testCaseClass, **kwargs):
        """Return a suite of all tests cases contained in
           testCaseClass."""
        if issubclass(testCaseClass, unittest.suite.TestSuite):
            raise TypeError("Test cases should not be derived from " +
                            "TestSuite. Maybe you meant to derive from" +
                            " TestCase?")
        testCaseNames = self.getTestCaseNames(testCaseClass)
        if not testCaseNames and hasattr(testCaseClass, 'runTest'):
            testCaseNames = ['runTest']

        # Modification here: parse keyword arguments to testCaseClass.
        test_cases = []
        for test_case_name in testCaseNames:
            test_cases.append(testCaseClass(test_case_name, **kwargs))
        loaded_suite = self.suiteClass(test_cases)

        return loaded_suite


class DAGTests(unittest.TestCase):

    def __init__(self, testName, app, test_instance=None, *args, **kwargs):
        unittest.TestCase.__init__(self, testName)
        self.app = app
        self.test_instance = test_instance

    def setUp(self) -> None:
        pass

    def test_schema_load(self):
        self.assertIsInstance(self.app.instance, dict)
        self.assertIsInstance(self.app.solution, dict)

    def test_try_solving_testcase(self):
        data = self.test_instance
        if data is None:
            return
        marshm = SchemaManager(self.app.instance).jsonschema_to_flask()
        marshm().load(data)
        solution, log, log_dict = self.app.solve(data, {})
        marshm = SchemaManager(self.app.solution).jsonschema_to_flask()
        marshm().load(solution)


def testAll():
    runner = unittest.TextTestRunner()
    suite_all = suite()
    # we run all tests at the same time
    ret = runner.run(suite_all)
    if not ret.wasSuccessful():
        raise RuntimeError("Tests were not passed")


def suite():
    apps = get_all_apps()
    loader = TestLoaderWithKwargs()
    suite = unittest.TestSuite()
    for app in apps:
        print("Testing app {}".format(app))
        try:
            test_instances = app.test_cases()
        except:
            tests = loader.loadTestsFromTestCase(DAGTests, app=app)
            suite.addTests(tests)
            continue
        for test in test_instances:
            tests = loader.loadTestsFromTestCase(DAGTests, app=app, test_instance=test)
            suite.addTests(tests)
    return suite


if __name__ == '__main__':
    testAll()