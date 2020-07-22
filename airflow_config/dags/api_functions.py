import requests

def sign_up(email, pwd, name):
    return requests.post(
        "http://127.0.0.1:5000/singup/",
        json={"email": email, "password": pwd, "name": name})


def login(email, pwd):
    response = requests.post(
        "http://127.0.0.1:5000/login/",
        json={"email": email, "password": pwd})
    
    return response.json()["token"]


def create_instance(token, data):
    response = requests.post(
        "http://127.0.0.1:5000/instance/",
        headers={'Authorization': 'access_token ' + token},
        json={"data": data})
    
    return response.json()["instance_id"]


def create_execution(token, instance_id, config):
    response = requests.post(
        "http://127.0.0.1:5000/execution/",
        headers={'Authorization': 'access_token ' + token},
        json={"config": config, "instance": instance_id})
    return response.json()["execution_id"]


def get_data(token, execution_id):
    response = requests.get(
        "http://127.0.0.1:5000/execution_data/",
        headers={'Authorization': 'access_token ' + token},
        json={"execution_id": execution_id})
    
    return response.json()


def write_solution(token, execution_id, solution, log_text=None, log_json=None):
    print("Writing the solution in database")
    response = requests.post(
        "http://127.0.0.1:5000/execution_data/",
        headers={'Authorization': 'access_token ' + token},
        json={"execution_id": execution_id, "execution_results": solution, "log_text": log_text, "log_json": log_json})
    
    return response







