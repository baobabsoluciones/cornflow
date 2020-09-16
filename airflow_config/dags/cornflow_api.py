import requests
from urllib.parse import urljoin


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
