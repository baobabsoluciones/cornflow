def register_deployed_dags_command(
    url: str = None, user: str = None, pwd: str = None, verbose: int = 0
):
    # Full imports
    import logging as log
    import time

    # Partial imports
    from sqlalchemy.exc import DBAPIError, IntegrityError

    # Internal modules imports
    from cornflow_client.airflow.api import Airflow
    from ..models import DeployedDAG
    from cornflow_core.shared import db

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

    dags_registered = [dag.id for dag in DeployedDAG.get_all_objects()]

    response = af_client.get_model_dags()
    dag_list = response.json()["dags"]

    processed_dags = [
        DeployedDAG({"id": dag["dag_id"], "description": dag["description"]})
        for dag in dag_list
        if dag["dag_id"] not in dags_registered
    ]

    if len(processed_dags) > 0:
        db.session.bulk_save_objects(processed_dags)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        log.error(f"Integrity error on deployed dags register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        log.error(f"Unknown error on deployed dags register: {e}")

    if verbose == 1:
        if len(processed_dags) > 0:
            print(f"DAGs registered: {processed_dags}")
        else:
            print("No new DAGs")
    return True


def register_deployed_dags_command_test(dags: list = None, verbose=0):
    from ..models import DeployedDAG

    if dags is None:
        dags = ["solve_model_dag", "gc", "timer"]

    deployed_dag = [DeployedDAG({"id": dag, "description": None}) for dag in dags]
    for dag in deployed_dag:
        dag.save()

    if verbose == 1:
        print("Registered DAGs")
