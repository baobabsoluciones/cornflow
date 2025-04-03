"""
Endpoint to check the health of the services.
It performs a health check to airflow and a health check to cornflow database
"""

import os

# Import from libraries
from cornflow_client.airflow.api import Airflow
from flask import current_app
from flask_apispec import marshal_with, doc

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import UserModel
from cornflow.schemas.health import HealthResponse
from cornflow.shared.const import (
    AIRFLOW_BACKEND,
    DATABRICKS_BACKEND,
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
)
from cornflow.shared.databricks import Databricks
from cornflow.shared.exceptions import EndpointNotImplemented


class HealthEndpoint(BaseMetaResource):
    @doc(description="Health check", tags=["Health"])
    @marshal_with(HealthResponse)
    def get(self):
        """
        The get function is a simple health check endpoint that returns the status of both cornflow and airflow.

        :return: A dictionary with the keys 'cornflow_status' and 'airflow_status' and the state of each service
        :rtype: dict
        :doc-author: baobab soluciones
        """
        
        backend_status = self.check_backend_status()

        cornflow_status = STATUS_UNHEALTHY
        

        if (
            UserModel.get_one_user_by_username(os.getenv("CORNFLOW_SERVICE_USER"))
            is not None
        ):
            cornflow_status = STATUS_HEALTHY

        current_app.logger.info(
            f"Health check: cornflow {cornflow_status}, backend {backend_status}"
        )
        return {"cornflow_status": cornflow_status, "backend_status": backend_status}

    def check_backend_status(self):
        if current_app.config["CORNFLOW_BACKEND"] == AIRFLOW_BACKEND:
            return self._check_airflow_status()
        elif current_app.config["CORNFLOW_BACKEND"] == DATABRICKS_BACKEND:
            return self._check_databricks_status()
        else:
            raise EndpointNotImplemented()

    @staticmethod
    def _check_airflow_status():
        af_client = Airflow.from_config(current_app.config)
        airflow_status = STATUS_UNHEALTHY
        if af_client.is_alive():
            airflow_status = STATUS_HEALTHY

        return airflow_status

    @staticmethod
    def _check_databricks_status():
        db_client = Databricks.from_config(current_app.config)
        databricks_status = STATUS_UNHEALTHY
        if db_client.is_alive():
            databricks_status = STATUS_HEALTHY
        
        return databricks_status