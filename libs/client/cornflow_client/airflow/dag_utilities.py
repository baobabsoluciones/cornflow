"""

"""

import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin

from cornflow_client import CornFlow, CornFlowApiError

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
    "owner": "baobab",
    "depends_on_past": False,
    "start_date": datetime(2020, 2, 1),
    "email": [""],
    "email_on_failure": False,
    "email_on_retry": False,
    "retry_delay": timedelta(minutes=1),
    "schedule_interval": None,
}


def get_schemas_from_file(_dir, dag_name):
    # TODO: check if in use
    with open(os.path.join(_dir, dag_name + "_input.json"), "r") as f:
        instance = json.load(f)
    with open(os.path.join(_dir, dag_name + "_output.json"), "r") as f:
        solution = json.load(f)
    return instance, solution


def get_requirements(path):
    """
    Read requirements.txt from a project and return a list of packages.

    :param path: The path of the project
    :return: A list of required packages
    """
    # TODO: check if in use
    req_path = f"{path}/requirements.txt"

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

    :return: A logged and connected cornflow client class instance
    """
    # This secret comes from airflow configuration
    print("Getting connection information from ENV VAR=CF_URI")
    uri = secrets.get_conn_value("CF_URI")
    conn = urlparse(uri)
    scheme = conn.scheme
    if scheme == "cornflow":
        scheme = "http"
    url = f"{scheme}://{conn.hostname}"
    if conn.port:
        url = f"{url}:{conn.port}"
    if conn.path:
        url = urljoin(url, conn.path)
    airflow_user = CornFlow(url=url)
    airflow_user.login(username=conn.username, pwd=conn.password)
    return airflow_user


def try_to_save_error(client, exec_id, state=-1):
    """
    Attempt at saving that the execution failed
    """
    try:
        client.raw.put_api_for_id("dag/", id=exec_id, payload=dict(state=state))
    except Exception as e:
        print(f"An exception trying to register the failed status: {e}")


def try_to_save_airflow_log(client, exec_id, ti, base_log_folder):
    log_file = os.path.join(
        base_log_folder,
        f"{ti.dag_id}",
        f"{ti.task_id}",
        f"{ti.run_id}".replace("manual__", "").replace("scheduled__", ""),
        f"{ti.try_number}.log",
    )
    if os.path.exists(log_file):
        with open(log_file, "r") as fd:
            log_file_txt = fd.read()
        try:
            client.raw.put_api_for_id(
                "dag/", id=exec_id, payload=dict(log_text=log_file_txt)
            )
        except Exception as e:
            print(f"An exception occurred while trying to register airflow log: {e}")


def try_to_write_solution(client, exec_id, payload):
    """
    Tries to write the payload into cornflow
    If it fails tries to write again that it failed.
    If it fails at least once: it raises an exception
    """
    execution_payload = dict(**payload)
    execution_payload.pop("inst_id")
    execution_payload.pop("inst_checks")
    try:
        client.write_solution(execution_id=exec_id, **execution_payload)
    except CornFlowApiError:
        try_to_save_error(client, exec_id, -6)
        # attempt to update the execution with a failed status.
        raise AirflowDagException("The writing of the solution failed")

    if payload.get("inst_checks") is not None:
        checks_payload = dict()
        checks_payload["checks"] = payload["inst_checks"]
        try:
            client.write_instance_checks(
                instance_id=payload["inst_id"], **checks_payload
            )
        except CornFlowApiError:
            try_to_save_error(client, exec_id, -6)
            raise AirflowDagException("The writing of the instance checks failed")


def get_schema(dag_name):
    # TODO: check if in use
    _file = os.path.join(os.path.dirname(__file__), f"{dag_name}_output.json")
    with open(_file, "r") as f:
        schema = json.load(f)
    return schema


def cf_solve_app(app, secrets, **kwargs):
    if kwargs["dag_run"].conf.get("checks_only"):
        return cf_check(app.check, app.name, secrets, **kwargs)
    else:
        return cf_solve(app.solve, app.name, secrets, **kwargs)


def cf_solve(fun, dag_name, secrets, **kwargs):
    """
    Connect to cornflow, ask for data, solve the problem and write the solution in cornflow

    :param fun: The function to use to solve the problem.
    :param dag_name: the name of the dag, to later search the output schema
    :param kwargs: other kwargs passed to the dag task.
    :return:
    """
    ti = kwargs["ti"]
    base_log_folder = kwargs["conf"].get("logging", "base_log_folder")
    config = dict()
    try:
        client = connect_to_cornflow(secrets)
        exec_id = kwargs["dag_run"].conf["exec_id"]
        execution_data = client.get_data(exec_id)
        execution_status = client.update_status(exec_id, {"status": 0})
        data = execution_data["data"]
        solution_data = execution_data["solution_data"]
        config = execution_data["config"]
        inst_id = execution_data["id"]

        solution, sol_checks, inst_checks, log, log_json = fun(
            data, config, solution_data
        )

        # We connect again to cornflow in case that more than 24 hours
        # have passed from the first time we connect
        client = connect_to_cornflow(secrets)

        payload = dict(
            state=1,
            log_json=log_json,
            log_text=log,
            solution_schema=dag_name,
            inst_checks=inst_checks,
            inst_id=inst_id,
        )
        if not solution:
            # No solution found: we just send everything to cornflow.
            if config.get("msg", True):
                print("No solution found: we save what we have.")
            try_to_write_solution(client, exec_id, payload)
            return "Solution was not saved"
        # There is a solution:
        # we first need to validate the schema.
        # If it's not: we change the status to Invalid
        # and take out the server validation of the schema\
        payload["data"] = solution

        if config.get("msg", True):
            print("A solution was found: we will first validate it")

        if sol_checks is not None:
            payload["checks"] = sol_checks

        try_to_write_solution(client, exec_id, payload)

        # The validation went correctly: can save the solution without problem
        return "Solution saved"

    except NoSolverException as e:
        if config.get("msg", True):
            print("No solver found !")
        # We reconnect in case the solver has been more than 24 hours solving before the error is raised
        client = connect_to_cornflow(secrets)
        try_to_save_error(client, exec_id, -1)
        client.update_status(exec_id, {"status": -1})
        try_to_save_airflow_log(client, exec_id, ti, base_log_folder)
        raise AirflowDagException(e)
    except MemoryError as e:
        # Python MemoryError is raised when the process runs out of memory.
        if config.get("msg", True):
            print("Memory error detected")
        # We reconnect in case the solver has been more than 24 hours solving before the error is raised
        client = connect_to_cornflow(secrets)
        try_to_save_error(client, exec_id, -8)
        client.update_status(exec_id, {"status": -8})
        try_to_save_airflow_log(client, exec_id, ti, base_log_folder)
        raise AirflowDagException(f"The execution ran out of memory: {e}")
    except Exception as e:
        if config.get("msg", True):
            print("Some error happened")
        # We reconnect in case the solver has been more than 24 hours solving before the error is raised
        client = connect_to_cornflow(secrets)
        log_file = construct_log_path(ti, base_log_folder)
        if detect_memory_error_from_logs(log_file):
            try_to_save_error(client, exec_id, -8)
            client.update_status(exec_id, {"status": -8})
            try_to_save_airflow_log(client, exec_id, ti, base_log_folder)
            raise AirflowDagException(f"The execution ran out of memory: {e}")
        else:
            try_to_save_error(client, exec_id, -1)
            client.update_status(exec_id, {"status": -1})
            try_to_save_airflow_log(client, exec_id, ti, base_log_folder)
            raise AirflowDagException(f"There was an error during the solving: {e}")


def detect_memory_error_from_logs(log_file_path):
    """
    Reads possible memory error messages from the log file.

    :param log_file_path: the path to the log file
    :return: True if a memory error is detected, False otherwise
    """
    if not os.path.exists(log_file_path):
        return False

    with open(log_file_path, 'r') as f:
        log_content = f.read()

    # Possible patterns that indicate a memory error
    memory_error_patterns = [
        "MemoryError",
        "Out of memory",
        "Cannot allocate memory",
        "Memory limit exceeded",
        "OOM killed",
        "Killed",
        "OOMKilled",
        "out of memory",
        "The node was low on resource: memory",
        "Container was terminated due to OOM"
    ]

    return any(pattern in log_content for pattern in memory_error_patterns)

def construct_log_path(ti, base_log_folder):
    """
    Constructs the path to the log file for a given task instance.

    :param ti: Task instance object
    :param base_log_folder: Base log folder path from Airflow configuration
    :return: Full path to the log file
    """
    return os.path.join(
        base_log_folder,
        f"{ti.dag_id}",
        f"{ti.task_id}",
        f"{ti.run_id}".replace("manual__", "").replace("scheduled__", ""),
        f"{ti.try_number}.log",
    )

def cf_check(fun, dag_name, secrets, **kwargs):
    """
    Connect to cornflow, ask for data, check the solution data and write the checks in cornflow
    :param fun: The function to use to check the data
    :param secrets: Environment variables
    :param kwargs: other kwargs passed to the dag task.
    :return:
    """
    ti = kwargs["ti"]
    base_log_folder = kwargs["conf"].get("logging", "base_log_folder")
    config = dict()
    try:
        client = connect_to_cornflow(secrets)
        exec_id = kwargs["dag_run"].conf["exec_id"]
        execution_data = client.get_data(exec_id)
        config = execution_data["config"]

        instance_data = execution_data["data"]
        inst_id = execution_data["id"]
        solution_data = execution_data["solution_data"]

        inst_checks, sol_checks, log_json = fun(instance_data, solution_data)

        if config.get("checks_only"):
            payload = dict(
                state=1,
                log_json=log_json,
                log_text="Data checked.",
                solution_schema=dag_name,
                inst_checks=inst_checks,
                inst_id=inst_id,
            )
        else:
            payload = dict(
                inst_checks=inst_checks,
                inst_id=inst_id,
                state=1,
            )

        if sol_checks is not None:
            payload["checks"] = sol_checks

        try_to_write_solution(client, exec_id, payload)

        case_id = kwargs["dag_run"].conf.get("case_id")
        if case_id is not None:
            checks_payload = dict(checks=payload["inst_checks"])
            if sol_checks is not None:
                checks_payload["solution_checks"] = sol_checks
            try:
                client.write_case_checks(case_id=case_id, **checks_payload)
            except CornFlowApiError:
                try_to_save_error(client, exec_id, -6)
                if config.get("msg", True):
                    print("An error occurred while trying to save the checks")
                try_to_save_airflow_log(client, exec_id, ti, base_log_folder)
                raise AirflowDagException("The writing of the case checks failed")

        # # The validation went correctly: can save the solution without problem
        return "Checks saved"

    except Exception as e:
        if config.get("msg", True):
            print("Some unknown error happened")
        try_to_save_error(client, exec_id, -1)
        client.update_status(exec_id, {"status": -1})
        try_to_save_airflow_log(client, exec_id, ti, base_log_folder)
        raise AirflowDagException(
            "There was an error during the verification of the data"
        )


def callback_email(context):
    from airflow.utils.email import send_email
    from airflow.secrets.environment_variables import EnvironmentVariablesBackend

    path_to_log = (
        f"./logs/dag_id={context['dag'].dag_id}/run_id={context['run_id']}"
        f"/task_id={context['ti'].task_id}/attempt=1.log"
    )

    environment = EnvironmentVariablesBackend().get_variable("ENVIRONMENT")
    notification_email = EnvironmentVariablesBackend().get_variable(
        "NOTIFICATION_EMAIL"
    )
    environment_name = os.getenv("AIRFLOW__WEBSERVER__INSTANCE_NAME", "CornflowEnv")

    title = f"Airflow. {environment_name} ({environment}). DAG/task error: {context['dag'].dag_id}/{context['ti'].task_id} Failed"
    body = f"""
        The DAG/task {context['dag'].dag_id}/{context['ti'].task_id} has failed.
        <br>
        The log is attached.
        """

    send_email(
        to=[
            notification_email,
        ],
        subject=title,
        html_content=body,
        files=[path_to_log],
    )


def callback_on_task_failure(context):
    from airflow.secrets.environment_variables import EnvironmentVariablesBackend

    """
    Airflow Scheduler callbacks always TaskInstance fails,
    even by OOM (SIGKILL) worker's death.
    """
    ti = context.get("ti")
    dag_run = context.get("dag_run")
    if not ti or not dag_run or not dag_run.conf:
        return

    exec_id = dag_run.conf.get("exec_id")
    if not exec_id:
        return

    log_file_path = ti.log_filepath

    try:
        oom = detect_memory_error_from_logs(log_file_path)
    except Exception:
        oom = False

    code = -8 if oom else -1

    try:
        secrets = EnvironmentVariablesBackend()
        client = connect_to_cornflow(secrets)
        client.update_status(exec_id, {"status": code})

        with open(log_file_path, "r") as f:
            snippet = f.read(10_000)
        client.raw.put_api_for_id(
            "dag/",
            id=exec_id,
            payload={"log_text": snippet},
        )
    except CornFlowApiError as err:
        ti.log.error(f"[callback_on_task_failure] fail to notify state {code}: {err}")


class NoSolverException(Exception):
    pass


class AirflowDagException(Exception):
    pass
