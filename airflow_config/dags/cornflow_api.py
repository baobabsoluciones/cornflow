import requests
from urllib.parse import urljoin


class CornFlow(object):

    def __init__(self, url, token=None):
        self.url = url
        self.token = token

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
        if not self.token:
            raise ValueError("Need to login first!")
        response = requests.post(
            urljoin(self.url, 'instance/'),
            headers={'Authorization': 'access_token ' + self.token},
            json={"data": data})
        return response.json()["instance_id"]

    def create_execution(self, instance_id, config):
        if not self.token:
            raise ValueError("Need to login first!")
        response = requests.post(
            urljoin(self.url, 'execution/'),
            headers={'Authorization': 'access_token ' + self.token},
            json={"config": config, "instance": instance_id})
        return response.json()["execution_id"]

    def get_data(self, execution_id):
        if not self.token:
            raise ValueError("Need to login first!")
        response = requests.get(
            urljoin(urljoin(self.url, 'dag/'), str(execution_id) + '/'),
            headers={'Authorization': 'access_token ' + self.token},
            json={})
        return response.json()

    def write_solution(self, execution_id, solution, log_text=None, log_json=None):
        if not self.token:
            raise ValueError("Need to login first!")
        response = requests.post(
            urljoin(urljoin(self.url, 'dag/'), str(execution_id) + '/'),
            headers={'Authorization': 'access_token ' + self.token},
            json={"execution_results": solution, "log_text": log_text, "log_json": log_json})
        return response
