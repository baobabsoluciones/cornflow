"""
Endpoints to get the schemas
"""

# Import from libraries
from cornflow_client.airflow.api import Airflow
from flask import current_app, request
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, doc
import logging as log

# Import from internal modules
from .meta_resource import MetaResource
from ..models import PermissionsDAG
from ..shared.authentication import Auth
from cornflow_backend.exceptions import AirflowError, NoPermission
from ..schemas.schemas import SchemaOneApp, SchemaListApp


class SchemaEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to obtain names of available apps
    """

    @doc(description="Get list of available apps", tags=["Schemas"])
    @Auth.auth_required
    @marshal_with(SchemaListApp(many=True))
    def get(self):
        """
        API method to get a list of dag names

        :return: A dictionary with a message and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        user = Auth.get_user_obj_from_header(request.headers)
        dags = PermissionsDAG.get_user_dag_permissions(user.id)
        available_dags = [{"name": dag.dag_id} for dag in dags]

        log.debug("User gets list of schema")
        return available_dags


class SchemaDetailsEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to obtain schemas for one app
    """

    @doc(description="Get instance, solution and config schema", tags=["Schemas"])
    @Auth.auth_required
    @marshal_with(SchemaOneApp)
    def get(self, dag_name):
        """
        API method to get the input, output and config schemas for a given dag

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

            log.debug("User gets schema {}".format(dag_name))
            # it exists: we try to get its schemas
            return af_client.get_schemas_for_dag_name(dag_name)
        else:
            raise NoPermission(
                error="User does not have permission to access this dag",
                status_code=403,
            )
