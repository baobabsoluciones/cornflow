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
            log.info(f"Airflow is not reachable (attempt {attempts})")
        time.sleep(15)

    if not af_client.is_alive():
        if verbose == 1:
            log.info("Airflow is not reachable")
        return False

    dags_registered = [dag.id for dag in DeployedDAG.get_all_objects()]

    response = af_client.get_model_dags()
    dag_list = response.json()["dags"]

    schemas = {
        dag["dag_id"]: af_client.get_schemas_for_dag_name(dag["dag_id"])
        for dag in dag_list
        if dag["dag_id"] not in dags_registered
    }

    processed_dags = [
        DeployedDAG({
            "id": dag["dag_id"],
            "description": dag["description"],
            "instance_schema": schemas[dag["dag_id"]]["instance"],
            "solution_schema": schemas[dag["dag_id"]]["solution"],
            "config_schema": schemas[dag["dag_id"]]["config"]
        })
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
            log.info(f"DAGs registered: {processed_dags}")
        else:
            log.info("No new DAGs")
    return True


def register_deployed_dags_command_test(dags: list = None, verbose=0):
    from ..models import DeployedDAG
    import logging as log

    if dags is None:
        dags = ["solve_model_dag", "gc", "timer"]

    deployed_dag = [
        DeployedDAG({
            "id": dag,
            "description": None,
            "instance_schema": dict(),
            "solution_schema": dict(),
            "config_schema": dict(),
        })
        for dag in dags]
    for dag in deployed_dag:
        dag.save()

    if verbose == 1:
        log.info("Registered DAGs")
