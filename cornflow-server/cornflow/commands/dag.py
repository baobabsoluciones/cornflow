def register_deployed_dags_command(
    url: str = None, user: str = None, pwd: str = None, verbose: bool = False
):
    # Full imports
    import time

    # Partial imports
    from sqlalchemy.exc import DBAPIError, IntegrityError
    from flask import current_app

    # Internal modules imports
    from cornflow_client.airflow.api import Airflow
    from cornflow.models import DeployedDAG
    from cornflow.shared import db
    from cornflow.shared.const import AIRFLOW_NOT_REACHABLE_MSG

    af_client = Airflow(url, user, pwd)
    max_attempts = 20
    attempts = 0
    while not af_client.is_alive() and attempts < max_attempts:
        attempts += 1
        if verbose:
            current_app.logger.info(f"{AIRFLOW_NOT_REACHABLE_MSG} (attempt {attempts})")
        time.sleep(15)

    if not af_client.is_alive():
        if verbose:
            current_app.logger.info(f"{AIRFLOW_NOT_REACHABLE_MSG}")
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
        DeployedDAG(
            {
                "id": dag["dag_id"],
                "description": dag["description"],
                "instance_schema": schemas[dag["dag_id"]]["instance"],
                "solution_schema": schemas[dag["dag_id"]]["solution"],
                "instance_checks_schema": schemas[dag["dag_id"]]["instance_checks"],
                "solution_checks_schema": schemas[dag["dag_id"]]["solution_checks"],
                "config_schema": schemas[dag["dag_id"]]["config"],
            }
        )
        for dag in dag_list
        if dag["dag_id"] not in dags_registered
    ]

    if len(processed_dags) > 0:
        db.session.bulk_save_objects(processed_dags)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error on deployed dags register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknown error on deployed dags register: {e}")

    if verbose:
        if len(processed_dags) > 0:
            current_app.logger.info(f"DAGs registered: {processed_dags}")
        else:
            current_app.logger.info("No new DAGs")
    return True


def register_deployed_dags_command_test(dags: list = None, verbose: bool = False):
    from cornflow.models import DeployedDAG
    from flask import current_app
    from cornflow_client import get_pulp_jsonschema, get_empty_schema

    if dags is None:
        dags = ["solve_model_dag", "gc", "timer"]

    deployed_dag = [
        DeployedDAG(
            {
                "id": "solve_model_dag",
                "description": None,
                "instance_schema": get_pulp_jsonschema(),
                "solution_schema": get_pulp_jsonschema(),
                "instance_checks_schema": dict(),
                "solution_checks_schema": dict(),
                "config_schema": get_empty_schema(solvers=["cbc", "PULP_CBC_CMD"]),
            }
        )
    ] + [
        DeployedDAG(
            {
                "id": dag,
                "description": None,
                "instance_schema": dict(),
                "solution_schema": dict(),
                "instance_checks_schema": dict(),
                "solution_checks_schema": dict(),
                "config_schema": dict(),
            }
        )
        for dag in dags[1:]
    ]
    for dag in deployed_dag:
        dag.save()

    if verbose:
        current_app.logger.info("Registered DAGs")
