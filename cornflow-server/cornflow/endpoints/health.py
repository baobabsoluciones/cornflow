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
    CORNFLOW_VERSION,
)
from cornflow_client.databricks.api import Databricks
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
        cornflow_version = CORNFLOW_VERSION

        if (
            UserModel.get_one_user_by_username(os.getenv("CORNFLOW_SERVICE_USER"))
            is not None
        ):
            cornflow_status = STATUS_HEALTHY

        current_app.logger.info(
            f"Health check: cornflow {cornflow_status}, backend {backend_status}"
        )
        return {
            "cornflow_status": cornflow_status,
            "backend_status": backend_status,
            "cornflow_version": cornflow_version,
        }

    def check_backend_status(self):
        if current_app.config["CORNFLOW_BACKEND"] == AIRFLOW_BACKEND:
            client = Airflow.from_config(current_app.config)
        elif current_app.config["CORNFLOW_BACKEND"] == DATABRICKS_BACKEND:
            client = Databricks.from_config(current_app.config)
        else:
            raise EndpointNotImplemented()
        if client.is_alive(current_app.config):
            return STATUS_HEALTHY
        return STATUS_UNHEALTHY
