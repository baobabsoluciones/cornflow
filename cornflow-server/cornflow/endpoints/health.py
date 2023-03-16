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
        current_app.logger.error("HEALTH ENDPOINT")
        current_app.logger.error(f"{current_app.config['AIRFLOW_USER']}")
        current_app.logger.error(f"{current_app.config['AIRFLOW_URL']}")
        current_app.logger.error(f"{current_app.config['AIRFLOW_PWD']}")
        print("HEALTH ENDPOINT")
        print(f"{current_app.config['AIRFLOW_USER']}")
        print(f"{current_app.config['AIRFLOW_URL']}")
        print(f"{current_app.config['AIRFLOW_PWD']}")
        af_client = Airflow.from_config(current_app.config)
        airflow_status = STATUS_HEALTHY
        cornflow_status = STATUS_HEALTHY
        if not af_client.is_alive():
            airflow_status = STATUS_UNHEALTHY
        try:
            if UserModel.get_one_user_by_username("service_user") is not None:
                cornflow_status = STATUS_HEALTHY
            else:
                cornflow_status = STATUS_UNHEALTHY
        except Exception:
            cornflow_status = STATUS_UNHEALTHY
        return {"cornflow_status": cornflow_status, "airflow_status": airflow_status}
