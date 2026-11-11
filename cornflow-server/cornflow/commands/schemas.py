def update_schemas_command(url, user, pwd, verbose: bool = False):
    import time
    from flask import current_app

    from cornflow_client.airflow.api import Airflow
    from cornflow_client.constants import AirflowError
    from cornflow.shared.const import AIRFLOW_NOT_REACHABLE_MSG

    af_client = Airflow(url, user, pwd)
    max_attempts = 20
    attempts = 0
    while not af_client.is_alive() and attempts < max_attempts:
        attempts += 1
        if verbose == 1:
            current_app.logger.info(f"{AIRFLOW_NOT_REACHABLE_MSG} (attempt {attempts})")
        time.sleep(15)

    if not af_client.is_alive():
        if verbose == 1:
            current_app.logger.info(f"{AIRFLOW_NOT_REACHABLE_MSG}")
        return False

    try:
        response = af_client.update_schemas()
    except AirflowError as err:
        current_app.logger.warning(f"The DAGs schemas were not updated: {err}")
        return False
    if response.status_code == 200:
        if verbose:
            current_app.logger.info("DAGs schemas updated")
    else:
        if verbose:
            current_app.logger.info("The DAGs schemas were not updated properly")

    return True


def update_dag_registry_command(url, user, pwd, verbose: bool = False):
    import time
    from flask import current_app

    from cornflow_client.airflow.api import Airflow
    from cornflow_client.constants import AirflowError
    from cornflow.shared.const import AIRFLOW_NOT_REACHABLE_MSG

    af_client = Airflow(url, user, pwd)
    max_attempts = 20
    attempts = 0
    while not af_client.is_alive() and attempts < max_attempts:
        attempts += 1
        if verbose == 1:
            current_app.logger.info(f"{AIRFLOW_NOT_REACHABLE_MSG} (attempt {attempts})")
        time.sleep(15)

    if not af_client.is_alive():
        if verbose == 1:
            current_app.logger.info(f"{AIRFLOW_NOT_REACHABLE_MSG}")
        return False

    try:
        response = af_client.update_dag_registry()
    except AirflowError as err:
        current_app.logger.warning(f"The DAG registry was not updated: {err}")
        return False
    if response.status_code == 200:
        if verbose:
            current_app.logger.info("DAGs schemas updated on cornflow")
    else:
        if verbose:
            current_app.logger.info("The DAGs schemas were not updated properly")

    return True
