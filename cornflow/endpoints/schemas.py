"""
Endpoints to get the schemas
"""

# Import from libraries
from cornflow_client.airflow.api import Airflow
from flask import current_app
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, use_kwargs, doc
import logging as log

# Import from internal modules
from .meta_resource import MetaResource
from ..shared.exceptions import AirflowError
from ..schemas.schemas import SchemaOneApp, SchemaRequest, SchemaListApp


class SchemaEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to obtain names of available apps
    """

    @doc(description="Get list of available apps", tags=["Schemas"])
    @marshal_with(SchemaListApp(many=True))
    def get(self):
        """
        API method to get a list of dag names

        :return: A dictionary with a message and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        af_client = Airflow.from_config(current_app.config)
        if not af_client.is_alive():
            log.error("Airflow not accessible when getting schemas")
            raise AirflowError(error="Airflow is not accessible")

        log.debug("User gets list of schema")
        return af_client.get_all_schemas()


class SchemaDetailsEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to obtain schemas for one app
    """

    @doc(description="Get instance, solution and config schema", tags=["Schemas"])
    @marshal_with(SchemaOneApp)
    def get(self, dag_name):
        """
        API method to get the input, output and config schemas for a given dag

        :return: A dictionary with a message and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        af_client = Airflow.from_config(current_app.config)
        if not af_client.is_alive():
            log.error("Airflow not accessible when getting schema {}".format(dag_name))
            raise AirflowError(error="Airflow is not accessible")

        # try airflow and see if dag_name exists
        af_client.get_dag_info(dag_name)

        log.debug("User gets schema {}".format(dag_name))
        # it exists: we try to get its schemas
        return af_client.get_schemas_for_dag_name(dag_name)
