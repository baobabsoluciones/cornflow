"""
Endpoints to get the example data from a DAG
"""

# Import from libraries
from cornflow_client.airflow.api import Airflow
from flask import current_app, request
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, doc
import logging as log
import json

# Import from internal modules
from .meta_resource import MetaResource
from ..models import PermissionsDAG
from ..shared.authentication import Auth
from ..shared.exceptions import AirflowError, NoPermission
from ..schemas.example_data import ExampleData


class ExampleDataDetailsEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to obtain schemas for one app
    """

    @doc(description="Get example data from DAG", tags=["DAG"])
    @Auth.auth_required
    @marshal_with(ExampleData)
    def get(self, dag_name):
        """
        API method to get example data for a given dag

        :return: A dictionary with a message and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        user = Auth.get_user_obj_from_header(request.headers)
        permission = PermissionsDAG.check_if_has_permissions(
            user_id=user.id, dag_id=dag_name
        )

        if permission:
            af_client = Airflow.from_config(current_app.config)
            if not af_client.is_alive():
                log.error(
                    "Airflow not accessible when getting schema {}".format(dag_name)
                )
                raise AirflowError(error="Airflow is not accessible")

            # try airflow and see if dag_name exists
            af_client.get_dag_info(dag_name)

            log.debug("User gets exampple data from {}".format(dag_name))

            variable_name = f"z_{dag_name}_examples"
            response = af_client.get_one_variable(variable_name)
            result = dict()
            result["examples"] = json.loads(response["value"])
            result["name"] = response["key"]

            return result
        else:
            raise NoPermission(
                error="User does not have permission to access this dag",
                status_code=403,
            )
