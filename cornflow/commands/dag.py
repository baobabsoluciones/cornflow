# TODO: add command to register if there is new DAGs.
#  This should be executed on each deployment.
def register_deployed_dags_command(url, user, pwd, verbose):
    import time

    #
    from cornflow_client.airflow.api import Airflow

    from sqlalchemy.exc import IntegrityError
    from ..models import DeployedDAG
    from ..shared.utils import db

    DeployedDAG.query.delete()
    db.session.commit()

    af_client = Airflow(url, user, pwd)
    max_attempts = 600
    attempts = 0
    while not af_client.is_alive() and attempts < max_attempts:
        attempts += 1
        if verbose == 1:
            print(f"Airflow is not reachable (attempt {attempts})")
        time.sleep(10)

    if not af_client.is_alive():
        if verbose == 1:
            print("Airflow is not reachable")
        return False

    dags_registered = [dag.id for dag in DeployedDAG.get_all_objects()]

    response = af_client.get_model_dags()
    dag_list = response.json["dags"]

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
        print("INTEGRITY ERROR")
        print(e)
        print(processed_dags)

    if verbose == 1:
        if len(processed_dags) > 0:
            print(f"DAGs registered: {processed_dags}")
        else:
            print("No new DAGs")
    return True
