"""

"""

# Import from libraries
from cornflow_client.airflow.api import Airflow
from flask import current_app
from flask_apispec import marshal_with, doc

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
        af_client = Airflow.from_config(current_app.config)
        airflow_status = STATUS_HEALTHY
        cornflow_status = STATUS_HEALTHY
        current_app.logger.error(f"AIRFLOW PING: {af_client.is_alive()}")
        ping = af_client.is_alive()

        if not ping:
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

        return {"cornflow_status": cornflow_status, "airflow_status": airflow_status}
