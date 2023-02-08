"""
Endpoints to get the schemas
"""

# Import from libraries
from cornflow_client.airflow.api import Airflow
from flask import current_app, request
from flask_apispec import marshal_with, doc
from cornflow_core.authentication import authenticate

# Import from internal modules
from ..models import PermissionsDAG
from ..shared.authentication import Auth
from cornflow_core.exceptions import AirflowError, NoPermission
from ..schemas.schemas import SchemaOneApp, SchemaListApp
from cornflow_core.resources import BaseMetaResource

from ..shared.const import ALL_DEFAULT_ROLES


class SchemaEndpoint(BaseMetaResource):
    """
    Endpoint used to obtain names of available apps
    """

    ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES

    @doc(description="Get list of available apps", tags=["Schemas"])
    @authenticate(auth_class=Auth())
    @marshal_with(SchemaListApp(many=True))
    def get(self):
        """
        API method to get a list of dag names

        :return: A dictionary with a message and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        user = Auth().get_user_from_header(request.headers)
        dags = PermissionsDAG.get_user_dag_permissions(user.id)
        available_dags = [{"name": dag.dag_id} for dag in dags]

        current_app.logger.info("User gets list of schema")
        return available_dags


class SchemaDetailsEndpoint(BaseMetaResource):
    """
    Endpoint used to obtain schemas for one app
    """

    ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES

    @doc(description="Get instance, solution and config schema", tags=["Schemas"])
    @authenticate(auth_class=Auth())
    @marshal_with(SchemaOneApp)
    def get(self, dag_name):
        """
        API method to get the input, output and config schemas for a given dag

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
                    "Airflow not accessible when getting schema {}".format(dag_name)
                )
                err = "Airflow is not accessible"
                raise AirflowError(
                    error=err,
                    log_txt=f"Error while user {self.get_user_id()} tries to get the schemas for dag {dag_name}. " + err
                )

            # try airflow and see if dag_name exists
            af_client.get_dag_info(dag_name)

            current_app.logger.info("User gets schema {}".format(dag_name))
            # it exists: we try to get its schemas
            return af_client.get_schemas_for_dag_name(dag_name)
        else:
            err = "User does not have permission to access this dag"
            raise NoPermission(
                error=err,
                status_code=403,
                log_txt=f"Error while user {self.get_user_id()} tries to get the schemas for dag {dag_name}. " + err
            )
