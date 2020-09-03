import requests
from urllib.parse import urljoin

# TODO: CORNFLOW_URL should be modifiable
#  maybe have an object that handles the session
CORNFLOW_URL = "http://127.0.0.1:5000"

def sign_up(email, pwd, name):

    return requests.post(
        urljoin(CORNFLOW_URL, 'signup/'),
        json={"email": email, "password": pwd, "name": name})


def login(email, pwd):
    response = requests.post(
        urljoin(CORNFLOW_URL, 'login/'),
        json={"email": email, "password": pwd})
    
    return response.json()["token"]


def create_instance(token, data):
    response = requests.post(
        urljoin(CORNFLOW_URL, 'instance/'),
        headers={'Authorization': 'access_token ' + token},
        json={"data": data})
    
    return response.json()["instance_id"]


def create_execution(token, instance_id, config):
    response = requests.post(
        urljoin(CORNFLOW_URL, 'execution/'),
        headers={'Authorization': 'access_token ' + token},
        json={"config": config, "instance": instance_id})
    return response.json()["execution_id"]


def get_data(token, execution_id):
    response = requests.get(
        urljoin(urljoin(CORNFLOW_URL, 'execution_data/'), str(execution_id) + '/'),
        headers={'Authorization': 'access_token ' + token},
        json={})
    
    return response.json()


def write_solution(token, execution_id, solution, log_text=None, log_json=None):
    response = requests.post(
        urljoin(urljoin(CORNFLOW_URL, 'execution_data/'), str(execution_id) + '/'),
        headers={'Authorization': 'access_token ' + token},
        json={"execution_results": solution, "log_text": log_text, "log_json": log_json})
    
    return response







