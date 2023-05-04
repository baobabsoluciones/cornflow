"""
Endpoints to get the example data from a DAG
"""

# Import from libraries
from cornflow_client.airflow.api import Airflow
from flask import current_app, request
from flask_apispec import marshal_with, doc
import json

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import PermissionsDAG
from cornflow.schemas.example_data import ExampleData
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import VIEWER_ROLE, PLANNER_ROLE, ADMIN_ROLE
from cornflow.shared.exceptions import AirflowError, NoPermission


class ExampleDataDetailsEndpoint(BaseMetaResource):
    """
    Endpoint used to obtain schemas for one app
    """

    ROLES_WITH_ACCESS = [VIEWER_ROLE, PLANNER_ROLE, ADMIN_ROLE]

    @doc(description="Get example data from DAG", tags=["DAG"])
    @authenticate(auth_class=Auth())
    @marshal_with(ExampleData)
    def get(self, dag_name):
        """
        API method to get example data for a given dag

        :return: A dictionary with a message and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        user = Auth().get_user_from_header(request.headers)
        permission = PermissionsDAG.check_if_has_permissions(
            user_id=user.id, dag_id=dag_name
        )

        if permission:
            af_client = Airflow.from_config(current_app.config)
            if not af_client.is_alive():
                current_app.logger.error(
                    "Airflow not accessible when getting data {}".format(dag_name)
                )
                raise AirflowError(error="Airflow is not accessible")

            # try airflow and see if dag_name exists
            af_client.get_dag_info(dag_name)

            current_app.logger.info("User gets example data from {}".format(dag_name))

            variable_name = f"z_{dag_name}_examples"
            response = af_client.get_one_variable(variable_name)
            result = dict()
            result["examples"] = json.loads(response["value"])
            result["name"] = response["key"]

            return result
        else:
            err = "User does not have permission to access this dag."
            raise NoPermission(
                error=err,
                status_code=403,
                log_txt=f"Error while user {user} tries to get example data for dag {dag_name}. " + err
            )
