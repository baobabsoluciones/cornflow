"""

"""

import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin

from cornflow_client import CornFlow, CornFlowApiError, ApplicationCore

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


def get_schemas_from_file(_dir: str, dag_name: str):
    # TODO: check if in use
    with open(os.path.join(_dir, dag_name + "_input.json"), "r") as f:
        instance = json.load(f)
    with open(os.path.join(_dir, dag_name + "_output.json"), "r") as f:
        solution = json.load(f)
    return instance, solution


def get_requirements(path: str):
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

    :return: A logged and connected Cornflow class instance
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


def try_to_save_error(client: CornFlow, exec_id: str, state=-1, api="dag/", **kwargs):
    """
    Attempt at saving that the execution failed
    """
    try:
        client.raw.put_api_for_id(api, id=exec_id, payload=dict(state=state), **kwargs)
    except Exception as e:
        print(f"An exception trying to register the failed status: {e}")


def try_to_save_error_report(
    client: CornFlow, id: int, state=-1, api="report/", **kwargs
):
    """
    Attempt at saving that the report failed
    It's different than the execution, because put uses form data in reports
    """
    try:
        client.raw.put_api_for_id(
            api,
            id=id,
            payload=None,
            data=dict(state=state),
            headers={"content_type": "multipart/form-data"},
            post_url="edit",
            **kwargs,
        )
    except Exception as e:
        print(f"An exception trying to register the failed status: {e}")


def try_to_save_airflow_log(client: CornFlow, exec_id: str, ti, base_log_folder: str):
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
            client.put_api_for_id(
                "dag/", id=exec_id, payload=dict(log_text=log_file_txt)
            )
        except Exception as e:
            print(f"An exception occurred while trying to register airflow log: {e}")


def try_to_write_solution(client: CornFlow, exec_id: str, payload: dict):
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


def get_schema(dag_name: str):
    # TODO: check if in use
    _file = os.path.join(os.path.dirname(__file__), f"{dag_name}_output.json")
    with open(_file, "r") as f:
        schema = json.load(f)
    return schema


def cf_solve_app(app: ApplicationCore, secrets, **kwargs):
    if kwargs["dag_run"].conf.get("checks_only"):
        return cf_check(app.check, app.name, secrets, **kwargs)
    else:
        return cf_solve(app.solve, app.name, secrets, **kwargs)


def cf_solve(fun: callable, dag_name: str, secrets, **kwargs):
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
        try_to_save_error(client, exec_id, -1)
        client.update_status(exec_id, {"status": -1})
        try_to_save_airflow_log(client, exec_id, ti, base_log_folder)
        raise AirflowDagException(e)
    except Exception as e:
        if config.get("msg", True):
            print("Some unknown error happened")
        try_to_save_error(client, exec_id, -1)
        client.update_status(exec_id, {"status": -1})
        try_to_save_airflow_log(client, exec_id, ti, base_log_folder)
        raise AirflowDagException("There was an error during the solving")


def cf_check(fun: callable, dag_name: str, secrets, **kwargs):
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


def cf_report(
    app: ApplicationCore,
    secrets,
    **kwargs,
):
    """
    Connect to cornflow, ask for data, generate the report for the execution

    :param app: the application from which to generate the report
    :param secrets: Environment variables
    :param kwargs: other kwargs passed to the dag task.
    :return:
    """
    # TODO: if this task fails, the dagrun should still be valid
    try:
        client = connect_to_cornflow(secrets)
        exec_id = kwargs["dag_run"].conf["exec_id"]

        execution_info = client.get_results(exec_id)
        # TODO: if execution does not have results, quit:
        if execution_info["state"] < 1:
            # no need to write report since it's not requested
            print("Execution has not been solved")
            return None

        config = execution_info["config"]
        report_config = config.get("report", {})
        if not report_config:
            # no need to write report since it's not requested
            print("We did not find a report config")
            return None
        print("Starting to write the report")
        report_name = report_config.get("name", "report")
        # we assume the contents of the config match name + description
        payload = dict(
            execution_id=exec_id,
            name=report_name,
            description=report_config.get("description"),
            state=0,  # RUNNING
        )
        # we create an empty report
        report = client.create_report(**payload)

        def my_try_to_save(state):
            return try_to_save_error_report(client, report["id"], state)

        # now we want to fill it with the report file
        execution_data = client.get_data(exec_id)
        input_data = execution_data["data"]
        solution_data = execution_data["solution_data"]

        # maybe all of this should be abstracted inside the app?
        # maybe the app should return an Experiment?
        experiment = app.get_solver(app.get_default_solver_name())
        my_experiment = experiment.from_dict(
            dict(instance=input_data, solution=solution_data)
        )

        print(f"Preparing to write the report: {report_name}")
        try:
            report_path = my_experiment.generate_report(report_name=report_name)
        except ModuleNotFoundError as e:
            my_try_to_save(-10)
            raise AirflowDagException("The generation of the report failed")
        except:
            my_try_to_save(-1)
            raise AirflowDagException("The generation of the report failed")
        if not os.path.exists(report_path):
            my_try_to_save(-1)
            raise AirflowDagException("The generation of the report failed")
        print("Saving the actual report in cornflow")
        client.put_one_report(report["id"], payload=dict(state=1), filename=report_path)
    except CornFlowApiError:
        raise AirflowDagException("The writing of the report failed")
    except Exception as e:
        raise AirflowDagException("An unknown error occurred: " + str(e))


def callback_email(context: dict):
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


class NoSolverException(Exception):
    pass


class AirflowDagException(Exception):
    pass
