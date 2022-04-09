"""

"""

# Import from libraries
from cornflow_client.airflow.api import Airflow
from flask import current_app
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, doc

# Import from internal modules
from ..schemas.health import HealthResponse
from ..shared.const import STATUS_HEALTHY, STATUS_UNHEALTHY
from cornflow_core.shared import database as db
from cornflow_core.resources import BaseMetaResource


class HealthEndpoint(BaseMetaResource, MethodResource):
    @doc(description="Health check", tags=["Health"])
    @marshal_with(HealthResponse)
    def get(self):
        af_client = Airflow.from_config(current_app.config)
        airflow_status = STATUS_HEALTHY
        cornflow_status = STATUS_HEALTHY
        if not af_client.is_alive():
            airflow_status = STATUS_UNHEALTHY
        try:
            db.engine.execute("SELECT 1")
        except Exception:
            cornflow_status = STATUS_UNHEALTHY
        return {"cornflow_status": cornflow_status, "airflow_status": airflow_status}
