"""

"""

# Import from libraries
from cornflow_client.airflow.api import Airflow
from flask import current_app
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, doc

# Import from internal modules
from .meta_resource import MetaResource
from ..schemas.health import HealthResponse
from ..shared.const import STATUS_HEALTHY, STATUS_UNHEALTHY
from ..shared.utils import db


class HealthEndpoint(MetaResource, MethodResource):
    @doc(description="Health check", tags=["Health"])
    @marshal_with(HealthResponse)
    def get(self):
        config = current_app.config
        airflow_conf = dict(
            url=config["AIRFLOW_URL"],
            user=config["AIRFLOW_USER"],
            pwd=config["AIRFLOW_PWD"],
        )
        af_client = Airflow(**airflow_conf)
        airflow_status = STATUS_HEALTHY
        cornflow_status = STATUS_HEALTHY
        if not af_client.is_alive():
            airflow_status = STATUS_UNHEALTHY
        try:
            db.engine.execute("SELECT 1")
        except Exception:
            cornflow_status = STATUS_UNHEALTHY
        return {"cornflow_status": cornflow_status, "airflow_status": airflow_status}
