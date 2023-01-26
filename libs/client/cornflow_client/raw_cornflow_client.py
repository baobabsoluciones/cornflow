"""

"""
# Full imports
import logging as log
import re
import requests

# Partial imports
from functools import wraps
from urllib.parse import urljoin


class RawCornFlow(object):
    """
    Base class to access cornflow-server
    """

    def __init__(self, url, token=None):
        self.url = url
        self.token = token

    def ask_token(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.token:
                raise CornFlowApiError("Need to login first!")
            return func(self, *args, **kwargs)

        return wrapper

    def log_call(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            log.debug(result.json())
            return result

        return wrapper

    def prepare_encoding(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            encoding = kwargs.get("encoding", "br")
            if encoding not in [
                "gzip",
                "compress",
                "deflate",
                "br",
                "identity",
            ]:
                encoding = "br"
            kwargs["encoding"] = encoding
            result = func(*args, **kwargs)
            return result

        return wrapper

    # def expect_201(func):
    #     return partial(expect_status, status=201)
    #
    # def expect_200(func):
    #     return partial(expect_status, status=200)

    def api_for_id(
        self,
        api,
        id=None,
        method="GET",
        post_url=None,
        query_args=None,
        encoding=None,
        **kwargs,
    ):
        """
        :param api: the resource in the server
        :param id: the id of the particular object
        :param method: HTTP method to apply
        :param post_url: optional action to apply
        :param query_args: query arguments for the request
        :param encoding: optional string with the type of encoding, if it is not specified it uses br encoding,
        options are: gzip, compress, deflate, br or identity
        :param kwargs: other arguments to requests.request

        :return: requests.request
        """
        if api[0] == "/" and self.url[-1] == "/":
            api = api[1:]

        url = f"{urljoin(self.url, api)}"

        if url[-1] != "/":
            url = f"{url}/"

        if id is not None:
            url = f"{url}{id}/"

        if post_url is not None:
            if post_url[-1] != "/":
                url = f"{url}{post_url}/"
            else:
                url = f"{url}{post_url}"

        if query_args is not None:
            url = f"{url}?"
            for key, value in query_args.items():
                url = f"{url}{key}={value}&"
            url = url[:-1]
        return requests.request(
            method=method,
            url=url,
            headers={
                "Authorization": "access_token " + self.token,
                "Content-Encoding": encoding,
            },
            **kwargs,
        )

    def get_api(self, api, method="GET", encoding=None, **kwargs):
        return requests.request(
            method=method,
            url=urljoin(self.url, api) + "/",
            headers={
                "Authorization": "access_token " + self.token,
                "Content-Encoding": encoding,
            },
            **kwargs,
        )

    @ask_token
    @prepare_encoding
    def get_api_for_id(self, api, id=None, post_url=None, encoding=None, **kwargs):
        """
        api_for_id with a GET request
        """

        return self.api_for_id(
            api=api, id=id, post_url=post_url, encoding=encoding, **kwargs, method="get"
        )

    @ask_token
    @prepare_encoding
    def delete_api_for_id(self, api, id, encoding=None, **kwargs):
        """
        api_for_id with a DELETE request
        """
        return self.api_for_id(
            api=api, id=id, encoding=encoding, **kwargs, method="delete"
        )

    @ask_token
    @prepare_encoding
    def put_api_for_id(self, api, id, payload, encoding=None, **kwargs):
        """
        api_for_id with a PUT request
        """
        return self.api_for_id(
            api=api, id=id, json=payload, method="put", encoding=encoding, **kwargs
        )

    @ask_token
    @prepare_encoding
    def patch_api_for_id(self, api, id, payload, encoding=None, **kwargs):
        """
        api_for_id with a PATCH request
        """
        return self.api_for_id(
            api=api, id=id, json=payload, method="patch", encoding=encoding, **kwargs
        )

    @ask_token
    @prepare_encoding
    def post_api_for_id(self, api, id, encoding=None, **kwargs):
        """
        api_for_id with a POST request
        """
        return self.api_for_id(
            api=api, id=id, method="post", encoding=encoding, **kwargs
        )

    @ask_token
    @prepare_encoding
    def create_api(self, api, encoding=None, **kwargs):
        return requests.post(
            urljoin(self.url, api),
            headers={
                "Authorization": "access_token " + self.token,
                "Content-Encoding": encoding,
            },
            **kwargs,
        )

    @log_call
    @prepare_encoding
    def sign_up(self, username, email, pwd, encoding=None):
        """
        Sign-up to the server. Creates a new user or returns error.

        :param str username: username
        :param str email: email
        :param str pwd: password
        :param str encoding: the type of encoding used in the call. Defaults to 'br'

        :return: a dictionary with a token inside
        """
        return requests.post(
            urljoin(self.url, "signup/"),
            json={"username": username, "password": pwd, "email": email},
            headers={"Content-Encoding": encoding},
        )

    @log_call
    def is_alive(self):
        """
        Asks the server if it's alive
        """
        return requests.get(urljoin(self.url, "health/"))

    @prepare_encoding
    def login(self, username, pwd, encoding=None):
        """
        Log-in to the server.

        :param str username: username
        :param str pwd: password
        :param str encoding: the type of encoding used in the call. Defaults to 'br'

        :return: a dictionary with a token inside
        """
        response = requests.post(
            urljoin(self.url, "login/"),
            json={"username": username, "password": pwd},
            headers={"Content-Encoding": encoding},
        )
        if response.status_code == 200:
            self.token = response.json()["token"]
        return response

    @ask_token
    @log_call
    @prepare_encoding
    def create_instance(
        self, data, name=None, description="", schema="solve_model_dag", encoding=None
    ):
        """
        Uploads an instance to the server

        :param dict data: data according to json-schema for the problem
        :param str name: name for instance
        :param str description: description of the instance
        :param str schema: name of problem to solve
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        if name is None:
            try:
                name = data["parameters"]["name"]
            except IndexError:
                raise CornFlowApiError("The `name` argument needs to be filled")
        payload = dict(data=data, name=name, description=description, schema=schema)
        return self.create_api("instance/", json=payload, encoding=encoding)

    @ask_token
    @log_call
    @prepare_encoding
    def create_case(
        self,
        name,
        schema,
        data=None,
        parent_id=None,
        description="",
        solution=None,
        encoding=None,
    ):
        """
        Uploads a case to the server

        :param dict data: data according to json-schema for the problem
        :param str name: name for case
        :param str description: description of case
        :param str schema: name of problem of case
        :param str parent_id: id of the parent directory in the tree structure
        :param dict solution: optional solution data to store inside case
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        payload = dict(
            name=name,
            description=description,
            schema=schema,
            parent_id=parent_id,
        )
        # Both data AND solution are optional.
        # data is optional in directories.
        # solutions in unsolved instances
        if data is not None:
            payload["data"] = data
        if solution is not None:
            payload["solution"] = solution
        return self.create_api("case/", json=payload, encoding=encoding)

    @ask_token
    @log_call
    @prepare_encoding
    def create_instance_file(
        self, filename, name, description="", minimize=True, encoding=None
    ):
        """
        Uploads a file to the server to be parsed into an instance

        :param str filename: path to filename to upload
        :param str name: name for instance
        :param str description: description of the instance
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        with open(filename, "rb") as file:
            return self.create_api(
                "instancefile/",
                data=dict(name=name, description=description, minimize=minimize),
                files=dict(file=file),
                encoding=encoding,
            )

    @log_call
    @ask_token
    @prepare_encoding
    def create_execution(
        self,
        instance_id,
        config,
        name="test1",
        description="",
        schema="solve_model_dag",
        encoding=None,
        run=True,
    ):
        """
        Creates an execution from a (previously) uploaded instance

        :param str instance_id: id for the instance
        :param str name: name for the execution
        :param str description: description of the execution
        :param dict config: execution configuration
        :param str schema: name of the problem to solve
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        :param bool run: if the execution should be run or not
        """
        api = "execution/"
        payload = dict(
            config=config,
            instance_id=instance_id,
            name=name,
            description=description,
            schema=schema,
        )
        if not run:
            api += "?run=0"
        return self.create_api(api, json=payload, encoding=encoding)

    @log_call
    @ask_token
    @prepare_encoding
    def relaunch_execution(
        self,
        execution_id,
        config,
        encoding=None,
        run=True,
    ):
        """
        Relaunches an existing execution

        :param str execution_id: id for the execution
        :param dict config: execution configuration
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        :param bool run: if the execution should be run or not
        """
        api = "execution/" + execution_id + "/relaunch/"
        payload = dict(
            config=config,
        )
        if not run:
            api += "?run=0"
        return self.create_api(api, json=payload, encoding=encoding)

    @log_call
    @ask_token
    @prepare_encoding
    def create_execution_data_check(
        self,
        execution_id,
        encoding=None,
        run=True,
    ):
        """
        Creates an execution to check the instance and solution of an execution

        :param str execution_id: id for the execution to check
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        :param bool run: if the execution should be run or not
        """
        api = "data-check/execution/"
        post_url = ""
        if not run:
            post_url = "?run=0"
        url = urljoin(urljoin(self.url, api) + "/", str(execution_id) + "/" + post_url)
        return requests.request(
            method="post",
            url=url,
            headers={
                "Authorization": "access_token " + self.token,
                "Content-Encoding": encoding,
            }
        )

    @log_call
    @ask_token
    @prepare_encoding
    def create_instance_data_check(
        self,
        instance_id,
        encoding=None,
        run=True,
    ):
        """
        Creates an execution to check an instance

        :param str instance_id: id for the instance to check
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        :param bool run: if the execution should be run or not
        """
        api = "data-check/instance/"
        post_url = ""
        if not run:
            post_url = "?run=0"
        url = urljoin(urljoin(self.url, api) + "/", str(instance_id) + "/" + post_url)
        return requests.request(
            method="post",
            url=url,
            headers={
                "Authorization": "access_token " + self.token,
                "Content-Encoding": encoding,
            }
        )

    @log_call
    @ask_token
    @prepare_encoding
    def create_case_data_check(
            self,
            case_id,
            encoding=None,
            run=True,
    ):
        """
        Creates an execution to check the instance and solution of a case

        :param str case_id: id for the case to check
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        :param bool run: if the execution should be run or not
        """
        api = "data-check/case/"
        post_url = ""
        if not run:
            post_url = "?run=0"
        url = urljoin(urljoin(self.url, api) + "/", str(case_id) + "/" + post_url)
        response = requests.request(
            method="post",
            url=url,
            headers={
                "Authorization": "access_token " + self.token,
                "Content-Encoding": encoding,
            }
        )

        if response.status_code != 201:
            raise CornFlowApiError(
                f"Expected a code 201, got a {response.status_code} error instead: {response.text}"
            )
        return response.json()

    @ask_token
    @prepare_encoding
    def get_data(self, execution_id, encoding=None):
        """
        Downloads the data from an execution

        :param str execution_id: id for the execution
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api_for_id(api="dag/", id=execution_id, encoding=encoding)

    @ask_token
    @prepare_encoding
    def write_solution(self, execution_id, encoding=None, **kwargs):
        """
        Edits an execution

        :param str execution_id: id for the execution
        :param kwargs: optional data to edit
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.put_api_for_id(
            "dag/", id=execution_id, encoding=encoding, payload=kwargs
        )

    @ask_token
    @prepare_encoding
    def write_instance_checks(self, instance_id, encoding=None, **kwargs):
        """"""
        return self.put_api_for_id(
            "dag/instance/", id=instance_id, encoding=encoding, payload=kwargs
        )

    @ask_token
    @prepare_encoding
    def write_case_checks(self, case_id, encoding=None, **kwargs):
        """"""
        return self.put_api_for_id(
            "dag/case/", id=case_id, encoding=encoding, payload=kwargs
        )

    @log_call
    @ask_token
    @prepare_encoding
    def stop_execution(self, execution_id, encoding=None):
        """
        Interrupts an ongoing execution

        :param str execution_id: id for the execution
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.post_api_for_id(
            api="execution/", id=execution_id, encoding=encoding
        )

    @ask_token
    @prepare_encoding
    def manual_execution(self, instance_id, config, name, encoding=None, **kwargs):
        """
        Uploads an execution from solution data

        :param str instance_id: id for the instance
        :param str name: name for execution
        :param str description: description of the execution
        :param dict config: execution configuration
        :param str schema: name of the problem to solve
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        :param kwargs: contents of the solution (inside data)
        """
        payload = dict(config=config, instance_id=instance_id, name=name, **kwargs)
        return self.create_api("dag/", json=payload, encoding=encoding)

    @log_call
    @ask_token
    @prepare_encoding
    def get_results(self, execution_id, encoding=None):
        """
        Downloads results from an execution

        :param str execution_id: id for the execution
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api_for_id(
            api="execution/", id=execution_id, encoding=encoding
        )

    @log_call
    @ask_token
    @prepare_encoding
    def get_status(self, execution_id, encoding=None):
        """
        Downloads the current status of an execution

        :param str execution_id: id for the execution
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api_for_id(
            api="execution/", id=execution_id, post_url="status", encoding=encoding
        )

    @log_call
    @ask_token
    @prepare_encoding
    def update_status(self, execution_id, payload, encoding=None):
        """
        Updates the status of the execution from queued to running when solved.

        :param str execution_id: id for the execution
        :param dict payload: code of the updated status for the execution
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.put_api_for_id(
            api="execution/",
            id=execution_id,
            payload=payload,
            encoding=encoding,
            post_url="status",
        )

    @log_call
    @ask_token
    @prepare_encoding
    def get_log(self, execution_id, encoding=None):
        """
        Downloads the log for an execution

        :param str execution_id: id for the execution
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api_for_id(
            api="execution/", id=execution_id, post_url="log", encoding=encoding
        )

    @log_call
    @ask_token
    @prepare_encoding
    def get_solution(self, execution_id, encoding=None):
        """
        Downloads the solution data for an execution

        :param str execution_id: id for the execution
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api_for_id(
            api="execution/", id=execution_id, post_url="data", encoding=encoding
        )

    @log_call
    @ask_token
    @prepare_encoding
    def get_all_instances(self, params=None, encoding=None):
        """
        Downloads all the user's instances

        :param dict params: optional filters
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api("instance", params=params, encoding=encoding)

    @log_call
    @ask_token
    @prepare_encoding
    def get_all_cases(self, params=None, encoding=None):
        """
        Downloads all the user's cases

        :param dict params: optional filters
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api("case", params=params, encoding=encoding)

    @log_call
    @ask_token
    @prepare_encoding
    def get_all_executions(self, params=None, encoding=None):
        """
        Downloads all the user's executions

        :param dict params: optional filters
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api("execution", params=params, encoding=encoding)

    @log_call
    @ask_token
    @prepare_encoding
    def get_all_users(self, encoding=None):
        """
        Downloads all the users in the server
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api("user", encoding=encoding)

    @log_call
    @ask_token
    @prepare_encoding
    def get_one_user(self, user_id, encoding=None):
        """
        Downloads all information on a user

        :param str user_id: user id
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api_for_id(api="user", id=user_id, encoding=encoding)

    @log_call
    @ask_token
    @prepare_encoding
    def get_one_instance(self, reference_id, encoding=None):
        """
        Downloads header of an instance

        :param str reference_id: id for the instance
        :param str encoding: the type of encoding used in the call. Defaults to 'br'

        """
        return self.get_api_for_id(
            api="instance", id=reference_id, encoding=encoding
        )

    @log_call
    @ask_token
    @prepare_encoding
    def get_one_instance_data(self, reference_id, encoding=None):
        """
        Downloads instance data

        :param str reference_id: id for the instance
        :param str encoding: the type of encoding used in the call. Defaults to 'br'

        """
        return self.get_api_for_id(
            api="instance", id=reference_id, post_url="data", encoding=encoding
        )

    @log_call
    @ask_token
    @prepare_encoding
    def get_one_case(self, reference_id, encoding=None):
        """
        Downloads header of a case

        :param str reference_id: id for the case
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api_for_id(api="case", id=reference_id, encoding=encoding)

    @log_call
    @ask_token
    @prepare_encoding
    def get_one_case_data(self, reference_id, encoding=None):
        """
        Downloads case data

        :param str reference_id: id for the case
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api_for_id(api="case", id=reference_id, post_url="data", encoding=encoding)

    @log_call
    @ask_token
    @prepare_encoding
    def put_one_case(self, reference_id, payload, encoding=None):
        """
        Edits a case

        :param int reference_id: id for the case
        :param dict payload: data to edit
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.put_api_for_id(
            api="case", id=reference_id, payload=payload, encoding=encoding
        )

    @log_call
    @ask_token
    @prepare_encoding
    def put_one_instance(self, reference_id, payload, encoding=None):
        """
        Edits an instance

        :param str reference_id: id for the instance
        :param dict payload: data to edit
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.put_api_for_id(
            api="instance", id=reference_id, payload=payload, encoding=encoding
        )

    @log_call
    @ask_token
    @prepare_encoding
    def put_one_execution(self, reference_id, payload, encoding=None):
        """
        Edits an execution

        :param str reference_id: id for the execution
        :param dict payload: data to edit
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.put_api_for_id(
            api="execution", id=reference_id, payload=payload, encoding=encoding
        )

    @log_call
    @ask_token
    @prepare_encoding
    def patch_one_case(self, reference_id, payload, encoding=None):
        """
        Patch a case

        :param str reference_id: id for the case
        :param dict payload: data to edit
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.patch_api_for_id(
            api="case", id=reference_id, payload=payload, encoding=encoding
        )

    @log_call
    @ask_token
    @prepare_encoding
    def delete_one_instance(self, reference_id, encoding=None):
        """
        Delete an instance

        :param str reference_id: id for the instance
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.delete_api_for_id(
            api="instance", id=reference_id, encoding=encoding
        )

    @log_call
    @ask_token
    @prepare_encoding
    def delete_one_case(self, reference_id, encoding=None):
        """
        Deletes a case

        :param int reference_id: id for the case
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.delete_api_for_id(
            api="case", id=reference_id, encoding=encoding
        )

    @log_call
    @ask_token
    @prepare_encoding
    def delete_one_execution(self, reference_id, encoding=None):
        """
        Deletes an execution

        :param int reference_id: id for the execution
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.delete_api_for_id(
            api="execution", id=reference_id, encoding=encoding
        )

    @ask_token
    @prepare_encoding
    def get_schema(self, dag_name, encoding=None):
        """
        Downloads schemas for a problem

        :param str dag_name: id for the problem
        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api_for_id(api="schema", id=dag_name, encoding=encoding)

    @ask_token
    @prepare_encoding
    def get_all_schemas(self, encoding=None):
        """
        Downloads all problems' (aka as app's) names

        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api("schema", encoding=encoding)

    @log_call
    @ask_token
    @prepare_encoding
    def get_deployed_dags(self, encoding=None):
        """
        Downloads the deployed dags in cornflow in order to update them

        :param str encoding: the type of encoding used in the call. Defaults to 'br'
        """
        return self.get_api("dag/deployed", encoding=encoding)

    @log_call
    @ask_token
    @prepare_encoding
    def create_deployed_dag(
        self, name: str = None, description: str = None, encoding=None
    ):
        if name is None:
            return {"error": "No dag name was given"}
        payload = dict(id=name, description=description)
        return self.create_api("dag/deployed/", json=payload, encoding=encoding)


class CornFlowApiError(Exception):
    """
    CornFlow returns an error
    """

    pass


def arg_to_value(
    some_string, replace_underscores_with_spaces=False, force_number=False
):
    if replace_underscores_with_spaces:
        some_string = re.sub(pattern=r"_", repl=r" ", string=some_string)
    if some_string[0] == "'" and some_string[-1] == "'":
        # this means its a string, no need to continue
        return some_string[1:-1]
    if not force_number:
        return some_string
    if some_string.isdigit():
        return int(some_string)
    # TODO: probably other edge cases, such as boolean.
    try:
        return float(some_string)
    except ValueError:
        return some_string


def get_tuple_from_root(rest: str, **kwargs):
    if not rest:
        # it matches exactly, no index.
        raise CornFlowApiError("There is not rest: there is just one variable")

    if rest[0] == "(":
        # key is a tuple.
        args = re.split(",_?", rest[1:-1])
        kwargs = {**kwargs, "force_number": True}
        new_args = [arg_to_value(arg, **kwargs) for arg in args if arg != ""]
        return tuple(new_args)
    # key is a single value
    return arg_to_value(rest, **kwargs)


def group_variables_by_name(_vars, names_list, **kwargs):
    # this is an experimental function that assumes the following:
    # 1. keys do not have special characters: -+[] ->/
    # 2. key can be a tuple or a single string.
    # 3. if a tuple, they can be an integer or a string.
    #
    # it dos not permit the nested dictionary format of variables
    # we copy it because we will be taking out already seen variables
    _vars = dict(_vars)
    __vars = {k: {} for k in names_list}
    for root in names_list:
        # 1. match root name to variables
        candidates = {name: obj for name, obj in _vars.items() if name.startswith(root)}
        # 2 extract and store said variables
        try:
            __vars[root] = {
                get_tuple_from_root(name[len(root) + 1 :], **kwargs): obj
                for name, obj in candidates.items()
            }
        except CornFlowApiError:
            __vars[root] = list(candidates.values())[0]
        # 3. take out from list
        for name in candidates:
            _vars.pop(name)
    return __vars
