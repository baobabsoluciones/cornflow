from cornflow_client import CornFlow
from datetime import datetime, timedelta
import model_functions as mf
from airflow import AirflowException
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
from urllib.parse import urlparse

# TODO: move these functions to cornflow client

def get_arg(arg, context):
    """
    Get an argument from the kwargs given to a task
    
    :param arg: The name fo the argument (string)
    :param context: The list of kwargs
    :return: The argument value.
    """
    return context["dag_run"].conf[arg]


def get_requirements(path):
    """
    Read requirements.txt from a project and return a list of packages.
    
    :param path: The path of the project
    :return: A list of required packages
    """
    req_path = path + "/requirements.txt"
    
    try:
        with open(req_path, "r") as file:
            req_list = file.read().splitlines()
    except:
        print("no requirement file in this path")
        return []
    
    return req_list

def connect_to_cornflow():
    """
    Create a connection to cornflow and log in with airflow admin user.
    
    :return: A logged and connected Cornflow class instance
    """
    # This secret comes from airflow configuration
    print("Getting connection information from ENV VAR=CF_URI")
    secrets = EnvironmentVariablesBackend()
    uri = secrets.get_conn_uri('CF_URI')
    conn = urlparse(uri)
    # TODO: what if https??
    url="http://{}:{}".format(conn.hostname, conn.port)

    airflow_user = CornFlow(url=url)
    airflow_user.login(email=conn.username, pwd=conn.password)
    return airflow_user


def cf_get_data(kwargs):
    """
    Connect to cornflow and ask for the input data corresponding to the execution id.
    
    :param kwargs: kwargs passed to the dag task.
    :return: A logged and connected Cornflow class instance, the input data, the input config.
    """
    exec_id = get_arg("exec_id", kwargs)
    
    # login
    airflow_user = connect_to_cornflow()
    print("starting to solve the model with execution %s" % exec_id)
    # get data
    execution_data = airflow_user.get_data(exec_id)
    
    return airflow_user, execution_data["data"], execution_data["config"]


def cf_solve(fun, solution_schema, **kwargs):
    """
    Connect to cornflow, ask for data, solve the problem and write the solution in cornflow
    
    :param fun: The function to use to solve the problem.
    :param solution_schema: the name of the schema of the solution
    :param kwargs: other kwargs passed to the dag task.
    :return:
    """
    exec_id = get_arg("exec_id", kwargs)
    airflow_user, data, config = cf_get_data(kwargs = kwargs)
    solution, log = fun(data, **config)
    if solution:
        payload = dict(execution_results = solution, log_text=log, solution_schema = solution_schema, state = 1)
    else:
        payload = dict(state = 1, log_text=log, solution_schema = "hk_solution_schema")
    
    # Send the solution to cornflow.
    message = airflow_user.put_api_for_id('dag/', id=exec_id, payload=payload)

    if solution:
        return "Solution saved"
