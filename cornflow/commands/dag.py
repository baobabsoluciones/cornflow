# TODO: add command to register if there is new DAGs.
#  This should be executed on each deployment.
def register_deployed_dags_command(verbose):
    # import time
    #
    # from cornflow_client.airflow.api import Airflow
    # from flask import current_app
    from sqlalchemy.exc import IntegrityError
    from ..models import DeployedDAG
    from ..shared.utils import db

    # af_client = Airflow.from_config(current_app.config)
    # max_attempts = 600
    # attempts = 0
    # while not af_client.is_alive() and attempts < max_attempts:
    #     attempts += 1
    #     if verbose == 1:
    #         print(f"Airflow is not reachable (attempt {attempts})")
    #     time.sleep(10)
    #
    # if not af_client.is_alive():
    #     if verbose == 1:
    #         print("Airflow is not reachable")
    #     return False

    # dags_registered = [dag.id for dag in DeployedDAG.get_all_objects()]

    # response = af_client.get_model_dags()
    # dag_list = response.json["dags"]
    dag_list = [
        "facility_location",
        "graph_coloring",
        "hk_2020_dag",
        "inventory_problem",
        "knapsack",
        "match_making",
        "production_scheduling",
        "roadef",
        "rostering",
        "solve_model_dag",
        "timer",
        "tsp",
        "university_exams",
        "vrp",
    ]
    processed_dags = [DeployedDAG({"id": dag, "description": None}) for dag in dag_list]

    if len(processed_dags) > 0:
        db.session.bulk_save_objects(processed_dags)

    try:
        db.session.commit()
    except IntegrityError as e:
        print("INTEGRITY ERROR")
        print(e)
        print(processed_dags)

    if verbose == 1:
        if len(processed_dags) > 0:
            print(f"DAGs registered: {processed_dags}")
        else:
            print("No new DAGs")
    return True
