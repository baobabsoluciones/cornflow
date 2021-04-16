from cornflow_client import CornFlow, CornFlowApiError, SchemaManager
from urllib.parse import urlparse
from datetime import datetime, timedelta
import json
import os

# TODO: convert everything to an object that encapsulates everything
#  to make it clear and avoid all the arguments.
# class DagApp(object):
#
#     def __init__(self, dag_name, secrets):
#         self.name = dag_name
#         self.secrets = secrets
#
#     def solve(self, data, config):
#         raise NotImplemented()
#
#     def test_cases(self):
#         raise NotImplemented()
#
#     pass


default_args = {
    'owner': 'baobab',
    'depends_on_past': False,
    'start_date': datetime(2020, 2, 1),
    'email': [''],
    'email_on_failure': False,
    'email_on_retry': False,
    'retry_delay': timedelta(minutes=1),
    'schedule_interval': None
}


def get_schemas_from_file(_dir, dag_name):
    with open(os.path.join(_dir, dag_name + '_input.json'), 'r') as f:
        instance = json.load(f)
    with open(os.path.join(_dir, dag_name + '_output.json'), 'r') as f:
        solution = json.load(f)
    return instance, solution


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


def connect_to_cornflow(secrets):
    """
    Create a connection to cornflow and log in with airflow admin user.

    :return: A logged and connected Cornflow class instance
    """
    # This secret comes from airflow configuration
    print("Getting connection information from ENV VAR=CF_URI")
    uri = secrets.get_conn_uri('CF_URI')
    conn = urlparse(uri)
    url = '{uri.scheme}://{uri.hostname}'.format(uri=conn)
    if conn.port:
        url += ':{uri.port}'.format(uri=conn)
    if conn.path:
        url += '{uri.path}/'.format(uri=conn)
    # TODO: delete this when migrated
    url2 = "http://{}:{}{}/".format(conn.hostname, conn.port, conn.path)
    try:
        airflow_user = CornFlow(url=url)
        airflow_user.login(email=conn.username, pwd=conn.password)
    except:
        airflow_user = CornFlow(url=url2)
        airflow_user.login(email=conn.username, pwd=conn.password)
    return airflow_user


def cf_get_data(client, kwargs):
    """
    Connect to cornflow and ask for the input data corresponding to the execution id.

    :param kwargs: kwargs passed to the dag task.
    :return: A logged and connected Cornflow class instance, the input data, the input config.
    """
    exec_id = get_arg("exec_id", kwargs)

    # login
    # airflow_user = connect_to_cornflow()
    print("starting to solve the model with execution %s" % exec_id)
    # get data
    execution_data = client.get_data(exec_id)

    return execution_data["data"], execution_data["config"]


def try_to_save_error(client, exec_id, state=-1):
    """
    Attempt at saving that the execution failed
    """
    try:
        client.put_api_for_id('dag/', id=exec_id, payload=dict(state=state))
    except Exception as e:
        print("An exception trying to register the failed status: {}".format(e))


def try_to_write_solution(client, exec_id, payload):
    """
    Tries to write the payload into cornflow
    If it fails tries to write again that it failed.
    If it fails at least once: it raises an exception
    """
    try:
        client.write_solution(execution_id=exec_id, **payload)
    except CornFlowApiError:
        try_to_save_error(client, exec_id, -6)
        # attempt to update the execution with a failed status.
        raise AirflowDagException('The writing of the solution failed')


def get_schema(dag_name):
    _file = os.path.join(os.path.dirname(__file__),
                         "{}_output.json".format(dag_name))
    with open(_file, 'r') as f:
        schema = json.load(f)
    return schema


def cf_solve(fun, dag_name, secrets, **kwargs):
    """
    Connect to cornflow, ask for data, solve the problem and write the solution in cornflow

    :param fun: The function to use to solve the problem.
    :param dag_name: the name of the dag, to later search the output schema
    :param kwargs: other kwargs passed to the dag task.
    :return:
    """
    exec_id = get_arg("exec_id", kwargs)
    client = connect_to_cornflow(secrets)
    data, config = cf_get_data(client, kwargs=kwargs)
    try:
        solution, log, log_json = fun(data, config)
    except NoSolverException as e:
        print("No solver found !")
        try_to_save_error(client, exec_id, -1)
        raise AirflowDagException(e)
    except Exception as e:
        print("Some unknown error happened")
        try_to_save_error(client, exec_id, -1)
        raise AirflowDagException('There was an error during the solving')
    payload = dict(state=1, log_json=log_json, log_text=log,
                   solution_schema=dag_name)
    if not solution:
        # No solution found: we just send everything to cornflow.
        print("No solution found: we save what we have.")
        try_to_write_solution(client, exec_id, payload)
        return "Solution was not saved"
    # There is a solution:
    # we first need to validate the schema.
    # If it's not: we change the status to Invalid
    # and take out the server validation of the schema\
    # TODO: not sure if this idea makes sense
    payload['data'] = solution
    print("A solution was found: we will first validate it")
    # try:
    #     schema = get_schema(dag_name)
    #     marshmallow_obj = SchemaManager(schema).jsonschema_to_flask()
    #     marshmallow_obj().load(solution)
    # except Exception as e:
    #     print("Validation failed! we will save it still. {}".format(e))
    #     payload['log_json']['status'] = 'Invalid'
    #     payload['solution_schema'] = None

    try_to_write_solution(client, exec_id, payload)

    # The validation went correctly: can save the solution without problem
    return "Solution saved"


class NoSolverException(Exception):
    pass


class AirflowDagException(Exception):
    pass
