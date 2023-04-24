"""
Endpoints to get the schemas
"""

# Import from libraries
from flask import current_app, request
from flask_apispec import marshal_with, doc

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import PermissionsDAG, DeployedDAG
from cornflow.schemas.schemas import SchemaOneApp, SchemaListApp
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import ALL_DEFAULT_ROLES
from cornflow.shared.exceptions import NoPermission


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
            deployed_dag = DeployedDAG.get_one_object(dag_name)
            current_app.logger.info("User gets schema {}".format(dag_name))
            return {
                "instance": deployed_dag.instance_schema,
                "solution": deployed_dag.solution_schema,
                "instance_checks": deployed_dag.instance_checks_schema,
                "solution_checks": deployed_dag.solution_checks_schema,
                "config": deployed_dag.config_schema,
                "name": dag_name
            }, 200
        else:
            err = "User does not have permission to access this dag"
            raise NoPermission(
                error=err,
                status_code=403,
                log_txt=f"Error while user {self.get_user()} tries to get the schemas for dag {dag_name}. "
                + err,
            )
