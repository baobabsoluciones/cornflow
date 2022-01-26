def update_schemas_command(url, user, pwd, verbose):
    import time

    #
    from cornflow_client.airflow.api import Airflow

    from sqlalchemy.exc import IntegrityError
    from ..models import DeployedDAG
    from ..shared.utils import db

    af_client = Airflow(url, user, pwd)
    max_attempts = 20
    attempts = 0
    while not af_client.is_alive() and attempts < max_attempts:
        attempts += 1
        if verbose == 1:
            print(f"Airflow is not reachable (attempt {attempts})")
        time.sleep(15)

    if not af_client.is_alive():
        if verbose == 1:
            print("Airflow is not reachable")
        return False

    response = af_client.update_schemas()
    if response.status_code == 200:
        if verbose == 1:
            print("DAGs schemas updated")
    else:
        if verbose == 1:
            print("The DAGs schemas were not updated properly")

    return True
