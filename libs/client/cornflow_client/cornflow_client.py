from .raw_cornflow_client import RawCornFlow, CornFlowApiError


class CornFlow:
    def __init__(self, url, token=None):
        self.raw = RawCornFlow(url, token)

        self.sign_up = self.expect_status(self.raw.sign_up, 201)
        self.create_instance = self.expect_status(self.raw.create_instance, 201)
        self.create_case = self.expect_status(self.raw.create_case, 201)
        self.create_instance_file = self.expect_status(self.raw.create_instance_file, 201)
        self.create_execution = self.expect_status(self.raw.create_execution, 201)
        self.relaunch_execution = self.expect_status(self.raw.relaunch_execution, 201)
        self.create_execution_data_check = self.expect_status(self.raw.create_execution_data_check, 201)
        self.create_instance_data_check = self.expect_status(self.raw.create_instance_data_check, 201)
        self.create_case_data_check = self.expect_status(self.raw.create_case_data_check, 201)
        self.get_data = self.expect_status(self.raw.get_data, 200)
        self.write_solution = self.expect_status(self.raw.write_solution, 200)
        self.write_instance_checks = self.expect_status(self.raw.write_instance_checks, 200)
        self.write_case_checks = self.expect_status(self.raw.write_case_checks, 200)
        self.stop_execution = self.expect_status(self.raw.stop_execution, 200)
        self.manual_execution = self.expect_status(self.raw.manual_execution, 201)
        self.get_results = self.expect_status(self.raw.get_results, 200)
        self.get_status = self.expect_status(self.raw.get_status, 200)
        self.update_status = self.expect_status(self.raw.update_status, 200)
        self.get_log = self.expect_status(self.raw.get_log, 200)
        self.get_solution = self.expect_status(self.raw.get_solution, 200)
        self.get_all_instances = self.expect_status(self.raw.get_all_instances, 200)
        self.get_all_cases = self.expect_status(self.raw.get_all_cases, 200)
        self.get_all_executions = self.expect_status(self.raw.get_all_executions, 200)
        self.get_all_users = self.expect_status(self.raw.get_all_users, 200)
        self.get_one_user = self.expect_status(self.raw.get_one_user, 200)
        self.get_one_instance = self.expect_status(self.raw.get_one_instance, 200)
        self.get_one_instance_data = self.expect_status(self.raw.get_one_instance_data, 200)
        self.get_one_case = self.expect_status(self.raw.get_one_case, 200)
        self.get_one_case_data = self.expect_status(self.raw.get_one_case_data, 200)
        self.put_one_case = self.expect_status(self.raw.put_one_case, 200)
        self.put_one_instance = self.expect_status(self.raw.put_one_instance, 200)
        self.put_one_execution = self.expect_status(self.raw.put_one_execution, 200)
        self.patch_one_case = self.expect_status(self.raw.patch_one_case, 200)
        self.delete_one_instance = self.expect_status(self.raw.delete_one_instance, 200)
        self.delete_one_case = self.expect_status(self.raw.delete_one_case, 200)
        self.delete_one_execution = self.expect_status(self.raw.delete_one_execution, 200)
        self.get_schema = self.expect_status(self.raw.get_schema, 200)
        self.get_all_schemas = self.expect_status(self.raw.get_all_schemas, 200)
        self.get_deployed_dags = self.expect_status(self.raw.get_deployed_dags, 200)
        self.create_deployed_dag = self.expect_status(self.raw.create_deployed_dag, 201)

    @property
    def url(self):
        """ Gets the url of the server """
        return self.raw.url

    @url.setter
    def url(self, url):
        """ Sets the url of the server """
        self.raw.url = url

    @property
    def token(self):
        """ Gets the token """
        return self.raw.token

    @token.setter
    def token(self, token):
        """ Sets the token """
        self.raw.token = token

    @staticmethod
    def expect_status(func, expected_status=None):
        """
        Gets the response of the call
        and raise an exception if the status of the response is not the expected
        """
        def decorator(*args, **kwargs):
            response = func(*args, **kwargs)
            if expected_status is not None and response.status_code != expected_status:
                raise CornFlowApiError(
                    f"Expected a code {expected_status}, got a {response.status_code} error instead: {response.text}"
                )
            return response.json()
        return decorator

    def is_alive(self):
        """
        Asks the server if it's alive
        """
        response = self.raw.is_alive()
        if response.status_code == 200:
            return response.json()
        raise CornFlowApiError(
            f"Connection failed with status code: {response.status_code}: {response.text}"
        )

    def login(self, username, pwd, encoding=None):
        """
        Log-in to the server.

        :param str username: username
        :param str pwd: password
        :param str encoding: the type of encoding used in the call. Defaults to 'br'

        :return: a dictionary with a token inside
        """
        response = self.raw.login(username, pwd, encoding=encoding)
        if response.status_code != 200:
            raise CornFlowApiError(
                f"Login failed with status code: {response.status_code}: {response.text}"
            )
        return response.json()
