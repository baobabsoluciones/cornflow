def update_schemas_command(url, user, pwd, verbose: bool = False):
    import time
    from flask import current_app

    from cornflow_client.airflow.api import Airflow

    af_client = Airflow(url, user, pwd)
    max_attempts = 20
    attempts = 0
    while not af_client.is_alive() and attempts < max_attempts:
        attempts += 1
        if verbose == 1:
            current_app.logger.info(f"Airflow is not reachable (attempt {attempts})")
        time.sleep(15)

    if not af_client.is_alive():
        if verbose == 1:
            current_app.logger.info("Airflow is not reachable")
        return False

    response = af_client.update_schemas()
    if response.status_code == 200:
        if verbose:
            current_app.logger.info("DAGs schemas updated")
    else:
        if verbose:
            current_app.logger.info("The DAGs schemas were not updated properly")

    return True
