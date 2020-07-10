"""

file to be copied in airflow/dags

"""


import requests
from pulp import *

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


def solve_model(data, config):
    print("Solving the model")
    var, model = LpProblem.from_dict(data)
    print(config)
    solver = get_solver_from_dict(config)
    model.solve(solver)
    solution = model.to_dict()
    
    log_path = config["logPath"]
    f = open(log_path, "r")
    log = f.read()
    
    print("Model solved")
    
    return solution, log


def write_solution(token, execution_id, solution, log_text=None, log_json=None):
    print("Writing the solution in database")
    response = requests.post(
        "http://127.0.0.1:5000/execution_data/",
        headers={'Authorization': 'access_token ' + token},
        json={"execution_id": execution_id, "execution_results": solution, "log_text": log_text, "log_json": log_json})
    
    return response


def solve_execution(token, execution_id):
    execution_data = get_data(token, execution_id)
    solution, log = solve_model(execution_data["data"], execution_data["config"])
    write_solution(token, execution_id, solution, log)
    
    return solution




