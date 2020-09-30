import requests
from urllib.parse import urljoin
import re

class CornFlow(object):

    def __init__(self, url, token=None):
        self.url = url
        self.token = token

    def require_token(self):
        if not self.token:
            raise ValueError("Need to login first!")

    def get_api_from_execution(self, api, execution_id):
        return requests.get(
            urljoin(urljoin(self.url, api), str(execution_id) + '/'),
            headers={'Authorization': 'access_token ' + self.token},
            json={})

    def sign_up(self, email, pwd, name):
        # TODO: do a login and return a token ?
        return requests.post(
            urljoin(self.url, 'signup/'),
            json={"email": email, "password": pwd, "name": name})

    def login(self, email, pwd):
        response = requests.post(
            urljoin(self.url, 'login/'),
            json={"email": email, "password": pwd})
        self.token = response.json()["token"]
        return self.token

    def create_instance(self, data):
        self.require_token()
        response = requests.post(
            urljoin(self.url, 'instance/'),
            headers={'Authorization': 'access_token ' + self.token},
            json={"data": data})
        return response.json()["instance_id"]

    def create_execution(self, instance_id, config):
        self.require_token()
        response = requests.post(
            urljoin(self.url, 'execution/'),
            headers={'Authorization': 'access_token ' + self.token},
            json={"config": config, "instance": instance_id})
        return response.json()["execution_id"]

    def get_data(self, execution_id):
        self.require_token()
        response = self.get_api_from_execution('dag/', execution_id)
        return response.json()

    def write_solution(self, execution_id, solution, log_text=None, log_json=None):
        self.require_token()
        response = requests.post(
            urljoin(urljoin(self.url, 'dag/'), str(execution_id) + '/'),
            headers={'Authorization': 'access_token ' + self.token},
            json={"execution_results": solution, "log_text": log_text, "log_json": log_json})
        return response

    def get_results(self, execution_id):
        self.require_token()
        response = self.get_api_from_execution('execution/', execution_id)
        return response.json()

    def get_status(self, execution_id):
        self.require_token()
        response = self.get_api_from_execution('execution/status/', execution_id)
        return response.json()


class CornFlowApiError(Exception):
    """
    CornFlow returns an error
    """
    pass


def arg_to_value(some_string, replace_underscores_with_spaces=False, force_number=False):
    if replace_underscores_with_spaces:
        some_string = re.sub(pattern=r'_', repl=r' ', string=some_string)
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

    if rest[0] == '(':
        # key is a tuple.
        args = re.split(',_?', rest[1:-1])
        kwargs = {**kwargs, 'force_number':True}
        new_args = [arg_to_value(arg, **kwargs) for arg in args if arg != '']
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
        candidates = {name: obj for name, obj in _vars.items() if
                      name.startswith(root)}
        # 2 extract and store said variables
        try:
            __vars[root] = {get_tuple_from_root(name[len(root)+1:], **kwargs): obj
                            for name, obj in candidates.items()}
        except CornFlowApiError:
            __vars[root] = list(candidates.values())[0]
        # 3. take out from list
        for name in candidates:
            _vars.pop(name)
    return __vars
