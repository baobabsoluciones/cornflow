# Import from libraries
from flask import request, current_app
from flask_restful import Resource
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, use_kwargs, doc

from cornflow_client.airflow.api import Airflow
from ..shared.authentication import Auth
from ..shared.exceptions import AirflowError, EndpointNotImplemented, InvalidUsage

import logging as log

class SchemaEndpoint(Resource, MethodResource):
    """
    Endpoint used to create a new execution or get all the executions and their information back
    """

    def __init__(self):
        super().__init__()

    @doc(description='Get one schema', tags=['Schemas'])
    @Auth.auth_required
    # @marshal_with(ExecutionDetailsEndpointResponse(many=True))
    def get(self, dag_name):
        """
        API method to get the input and output schemas for a given dag
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed or a list with all the executions
          created by the authenticated user) and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        config = current_app.config
        airflow_conf = dict(url=config['AIRFLOW_URL'], user=config['AIRFLOW_USER'], pwd=config['AIRFLOW_PWD'])

        af_client = Airflow(**airflow_conf)
        if not af_client.is_alive():
            err = "Airflow is not accessible"
            log.error(err)
            raise AirflowError(error=err)

        # try airflow and see if dag_name exists
        af_client.get_dag_info(dag_name)

        # it exists: we try to get its schemas
        return af_client.get_schemas_for_dag_name(dag_name)

