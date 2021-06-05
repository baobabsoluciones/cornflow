"""
Endpoints to get the schemas
"""

# Import from libraries
from cornflow_client.airflow.api import Airflow
from flask import current_app
from flask_apispec.views import MethodResource
from flask_apispec import doc

# Import from internal modules
from .meta_resource import MetaResource
from ..shared.exceptions import AirflowError

import logging as log


class SchemaEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to obtain schemas
    """

    def __init__(self):
        super().__init__()

    @doc(description="Get instance, solution and config schema", tags=["Schemas"])
    def get(self, dag_name):
        """
        API method to get the input, output and config schemas for a given dag

        :return: A dictionary with a message and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        config = current_app.config
        airflow_conf = dict(
            url=config["AIRFLOW_URL"],
            user=config["AIRFLOW_USER"],
            pwd=config["AIRFLOW_PWD"],
        )

        af_client = Airflow(**airflow_conf)
        if not af_client.is_alive():
            err = "Airflow is not accessible"
            log.error(err)
            raise AirflowError(error=err)

        # try airflow and see if dag_name exists
        af_client.get_dag_info(dag_name)

        # it exists: we try to get its schemas
        return af_client.get_schemas_for_dag_name(dag_name)
