from urllib.parse import urljoin
import re
import logging as log
import requests
from functools import partial, wraps

# def expect_status(func, status):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         response = func(*args, **kwargs)
#         if response.status_code != status:
#             raise CornFlowApiError("Expected a code {}, got a {} error instead: {}".
#                                    format(status, response.status_code, response.text))
#         return response
#
#     return wrapper


class CornFlow(object):
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
            log.debug(result)
            return result

        return wrapper

    # def expect_201(func):
    #     return partial(expect_status, status=201)
    #
    # def expect_200(func):
    #     return partial(expect_status, status=200)

    def api_for_id(self, api, id, method, post_url="", **kwargs):
        if post_url and post_url[-1] != "/":
            post_url += "/"
        url = urljoin(urljoin(self.url, api) + "/", str(id) + "/" + post_url)
        return requests.request(
            method=method,
            url=url,
            headers={"Authorization": "access_token " + self.token},
            **kwargs
        )

    @ask_token
    def get_api_for_id(self, api, id, post_url="", **kwargs):
        return self.api_for_id(
            api=api, id=id, post_url=post_url, **kwargs, method="get"
        )

    @ask_token
    def delete_api_for_id(self, api, id, **kwargs):
        return self.api_for_id(api=api, id=id, **kwargs, method="delete")

    @ask_token
    def put_api_for_id(self, api, id, payload, **kwargs):
        return self.api_for_id(api=api, id=id, json=payload, method="put", **kwargs)

    @ask_token
    def patch_api_for_id(self, api, id, payload, **kwargs):
        return self.api_for_id(api=api, id=id, json=payload, method="patch", **kwargs)

    @ask_token
    def post_api_for_id(self, api, id, **kwargs):
        return self.api_for_id(api=api, id=id, method="post", **kwargs)

    @ask_token
    def create_api(self, api, **kwargs):
        return requests.post(
            urljoin(self.url, api),
            headers={"Authorization": "access_token " + self.token},
            **kwargs
        )

    @log_call
    def sign_up(self, username, email, pwd):
        return requests.post(
            urljoin(self.url, "signup/"),
            json={"username": username, "password": pwd, "email": email},
        )

    @log_call
    def is_alive(self):
        response = requests.get(urljoin(self.url, "health/"))
        if response.status_code == 200:
            return response.json()
        raise CornFlowApiError(
            "Connection failed with status code: {}: {}".format(
                response.status_code, response.text
            )
        )

    def login(self, username, pwd):
        response = requests.post(
            urljoin(self.url, "login/"), json={"username": username, "password": pwd}
        )
        if response.status_code == 200:
            result = response.json()
            self.token = result["token"]
            return result
        else:
            raise CornFlowApiError(
                "Login failed with status code: {}: {}".format(
                    response.status_code, response.text
                )
            )

    # TODO: those status_code checks should be done via a decorator. But I do not know how.
    @ask_token
    @log_call
    def create_instance(
        self, data, name=None, description="", schema="solve_model_dag"
    ):
        if name is None:
            try:
                name = data["parameters"]["name"]
            except IndexError:
                raise CornFlowApiError("The `name` argument needs to be filled")
        payload = dict(data=data, name=name, description=description, schema=schema)
        response = self.create_api("instance/", json=payload)
        if response.status_code != 201:
            raise CornFlowApiError(
                "Expected a code 201, got a {} error instead: {}".format(
                    response.status_code, response.text
                )
            )
        return response.json()

    def create_case(
        self, name, schema, data=None, parent_id=None, description="", solution=None
    ):
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
        response = self.create_api("case/", json=payload)
        if response.status_code != 201:
            raise CornFlowApiError(
                "Expected a code 201, got a {} error instead: {}".format(
                    response.status_code, response.text
                )
            )
        return response.json()

    @ask_token
    @log_call
    def create_instance_file(self, filename, name, description="", minimize=True):
        with open(filename, "rb") as file:
            response = self.create_api(
                "instancefile/",
                data=dict(name=name, description=description, minimize=minimize),
                files=dict(file=file),
            )

        if response.status_code != 201:
            raise CornFlowApiError(
                "Expected a code 201, got a {} error instead: {}".format(
                    response.status_code, response.text
                )
            )
        return response.json()

    @log_call
    @ask_token
    def create_execution(
        self,
        instance_id,
        config,
        name="test1",
        description="",
        schema="solve_model_dag",
    ):
        payload = dict(
            config=config,
            instance_id=instance_id,
            name=name,
            description=description,
            schema=schema,
        )
        response = self.create_api("execution/", json=payload)
        if response.status_code != 201:
            raise CornFlowApiError(
                "Expected a code 201, got a {} error instead: {}".format(
                    response.status_code, response.text
                )
            )
        return response.json()

    @ask_token
    def get_data(self, execution_id):
        response = self.get_api_for_id(api="dag/", id=execution_id)
        return response.json()

    @ask_token
    def write_solution(self, execution_id, **kwargs):
        response = self.put_api_for_id("dag/", id=execution_id, payload=kwargs)
        if response.status_code != 201:
            raise CornFlowApiError(
                "Expected a code 201, got a {} error instead: {}".format(
                    response.status_code, response.text
                )
            )
        return response.json()

    @log_call
    @ask_token
    def stop_execution(self, execution_id):
        response = self.post_api_for_id(api="execution/", id=execution_id)
        if response.status_code != 200:
            raise CornFlowApiError(
                "Expected a code 200, got a {} error instead: {}".format(
                    response.status_code, response.text
                )
            )
        return response.json()

    @ask_token
    def manual_execution(self, instance_id, config, name, **kwargs):
        payload = dict(config=config, instance_id=instance_id, name=name, **kwargs)
        response = self.create_api("dag/", json=payload)
        if response.status_code != 201:
            raise CornFlowApiError(
                "Expected a code 201, got a {} error instead: {}".format(
                    response.status_code, response.text
                )
            )
        return response.json()

    @log_call
    @ask_token
    def get_results(self, execution_id):
        response = self.get_api_for_id(api="execution/", id=execution_id)
        return response.json()

    @log_call
    @ask_token
    def get_status(self, execution_id):
        response = self.get_api_for_id(
            api="execution/", id=execution_id, post_url="status"
        )
        return response.json()

    @log_call
    @ask_token
    def get_log(self, execution_id):
        response = self.get_api_for_id(
            api="execution/", id=execution_id, post_url="log"
        )
        return response.json()

    @log_call
    @ask_token
    def get_solution(self, execution_id):
        response = self.get_api_for_id(
            api="execution/", id=execution_id, post_url="data"
        )
        return response.json()

    @log_call
    @ask_token
    def get_all_instances(self, params=None):
        response = requests.get(
            urljoin(self.url, "instance/"),
            headers={"Authorization": "access_token " + self.token},
            json={},
            params=params,
        )
        return response.json()

    @log_call
    @ask_token
    def get_all_cases(self, params=None):
        response = requests.get(
            urljoin(self.url, "case/"),
            headers={"Authorization": "access_token " + self.token},
            json={},
            params=params,
        )
        return response.json()

    @log_call
    @ask_token
    def get_all_executions(self, params=None):
        response = requests.get(
            urljoin(self.url, "execution/"),
            headers={"Authorization": "access_token " + self.token},
            json={},
            params=params,
        )
        return response.json()

    @log_call
    @ask_token
    def get_all_users(self):
        return requests.get(
            urljoin(self.url, "user/"),
            headers={"Authorization": "access_token " + self.token},
            json={},
        )

    @log_call
    @ask_token
    def get_one_user(self, user_id):
        return self.get_api_for_id(api="user", id=user_id)

    @log_call
    @ask_token
    def get_one_instance(self, reference_id):
        response = self.get_api_for_id(api="instance", id=reference_id)
        return response.json()

    @log_call
    @ask_token
    def get_one_case(self, reference_id):
        response = self.get_api_for_id(api="case", id=reference_id)
        return response.json()

    @log_call
    @ask_token
    def delete_one_case(self, reference_id):
        response = self.delete_api_for_id(api="case", id=reference_id)
        return response.json()

    @log_call
    @ask_token
    def put_one_case(self, reference_id, payload):
        response = self.put_api_for_id(api="case", id=reference_id, payload=payload)
        return response.json()

    @log_call
    @ask_token
    def patch_one_case(self, reference_id, payload):
        response = self.patch_api_for_id(api="case", id=reference_id, payload=payload)
        return response.json()

    @log_call
    @ask_token
    def delete_one_instance(self, reference_id):
        response = self.delete_api_for_id(api="instance", id=reference_id)
        return response

    @ask_token
    def get_schema(self, dag_name):
        response = self.get_api_for_id(api="schema", id=dag_name)
        return response.json()


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
