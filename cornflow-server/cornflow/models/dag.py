"""

"""
# Import from libraries
from sqlalchemy.dialects.postgresql import TEXT, JSON

# Import from internal modules
from cornflow_core.models import TraceAttributesModel
from cornflow_core.shared import db
from cornflow_client.airflow.api import Airflow
from cornflow_client.constants import (
    INSTANCE_SCHEMA,
    SOLUTION_SCHEMA,
    INSTANCE_CHECKS_SCHEMA,
    SOLUTION_CHECKS_SCHEMA
)


class DeployedDAG(TraceAttributesModel):
    """
    This model contains the registry of the DAGs that are deployed on the corresponding Airflow server
    """

    __tablename__ = "deployed_dags"
    id = db.Column(db.String(128), primary_key=True)
    description = db.Column(TEXT, nullable=True)
    instance_schema = db.Column(JSON, nullable=True)
    solution_schema = db.Column(JSON, nullable=True)
    config_schema = db.Column(JSON, nullable=True)
    instance_checks_schema = db.Column(JSON, nullable=True)
    solution_checks_schema = db.Column(JSON, nullable=True)

    dag_permissions = db.relationship(
        "PermissionsDAG",
        cascade="all,delete",
        backref="deployed_dags",
        primaryjoin="and_(DeployedDAG.id==PermissionsDAG.dag_id)",
    )

    def __init__(self, data):
        super().__init__()
        self.id = data.get("id")
        self.description = data.get("description", None)
        self.instance_schema = data.get("instance_schema", None)
        self.solution_schema = data.get("solution_schema", None)
        self.instance_checks_schema = data.get("instance_checks_schema", None)
        self.solution_checks_schema = data.get("solution_checks_schema", None)
        self.config_schema = data.get("config_schema", None)

    def __repr__(self):
        return f"<DAG {self.id}>"

    @staticmethod
    def get_one_schema(config, dag_name, schema=INSTANCE_SCHEMA):
        item = DeployedDAG.get_one_object(dag_name)

        # If the DAG is not up-to-date in the database, we ask Airflow
        if item is None:
            return Airflow.from_config(config).get_one_schema(dag_name, schema)

        if schema == INSTANCE_SCHEMA:
            return item.instance_schema
        elif schema == SOLUTION_SCHEMA:
            return item.solution_schema
        elif schema == INSTANCE_CHECKS_SCHEMA:
            return item.instance_checks_schema
        elif schema == SOLUTION_CHECKS_SCHEMA:
            return item.solution_checks_schema
        else:           # schema == CONFIG_SCHEMA
            return item.config_schema

