"""

"""

# Import from libraries
from cornflow_client.airflow.api import Airflow
from flask import current_app
from flask_apispec import marshal_with, doc
import requests

# Import from internal modules
from cornflow.schemas.health import HealthResponse
from cornflow.shared.const import STATUS_HEALTHY, STATUS_UNHEALTHY
from cornflow_core.shared import db
from cornflow_core.resources import BaseMetaResource
from cornflow.models import UserModel


class HealthEndpoint(BaseMetaResource):
    @doc(description="Health check", tags=["Health"])
    @marshal_with(HealthResponse)
    def get(self):
        try:
            current_app.logger.info("Health check")
            url = f"{current_app.config['AIRFLOW_URL']}/api/v1/health"
            current_app.logger.info(f"Health url: {url}")

            response = requests.get(
                url,
                headers={
                    "Content-type": "application/json",
                    "Accept": "application/json",
                },
            )

            current_app.logger.error(
                f"AIRFLOW RESPONSE: {response.status_code}, {response.json()}"
            )

            data = response.json()

            if (
                data["metadatabase"]["status"] == "healthy"
                and data["scheduler"]["status"] == "healthy"
            ):
                airflow_status = STATUS_HEALTHY
            else:
                airflow_status = STATUS_UNHEALTHY

            try:
                current_app.logger.error(
                    f"Service user: {UserModel.get_one_user_by_username('service_user')}"
                )
                if UserModel.get_one_user_by_username("service_user") is not None:
                    cornflow_status = STATUS_HEALTHY
                else:
                    cornflow_status = STATUS_UNHEALTHY
            except Exception:
                cornflow_status = STATUS_UNHEALTHY

            return {
                "cornflow_status": cornflow_status,
                "airflow_status": airflow_status,
            }
        except Exception as e:
            current_app.logger.error(f"Unexpected Exception: {e}")
            return {
                "cornflow_status": STATUS_UNHEALTHY,
                "airflow_status": STATUS_UNHEALTHY,
            }
