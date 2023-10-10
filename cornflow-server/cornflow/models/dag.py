"""

"""
# Import from libraries
from cornflow_client.airflow.api import Airflow
from cornflow_client.constants import (
    INSTANCE_SCHEMA,
    SOLUTION_SCHEMA,
    INSTANCE_CHECKS_SCHEMA,
    SOLUTION_CHECKS_SCHEMA
)
from sqlalchemy.dialects.postgresql import TEXT, JSON

# Import from internal modules
from cornflow.models.meta_models import TraceAttributesModel
from cornflow.shared import db
from cornflow.shared.exceptions import ObjectDoesNotExist


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

        if item is None:
            err = f"The DAG {dag_name} does not exist in the database."
            raise ObjectDoesNotExist(
                err,
                log_txt=f"Error while user tries to register data for DAG {dag_name} "
                            f"from instance and execution. " + err
            )

        if schema == INSTANCE_SCHEMA:
            jsonschema = item.instance_schema
        elif schema == SOLUTION_SCHEMA:
            jsonschema = item.solution_schema
        elif schema == INSTANCE_CHECKS_SCHEMA:
            jsonschema = item.instance_checks_schema
        elif schema == SOLUTION_CHECKS_SCHEMA:
            jsonschema = item.solution_checks_schema
        # schema == CONFIG_SCHEMA
        else:
            jsonschema = item.config_schema

        if jsonschema is None:
            # If the DAG is not up-to-date in the database, we ask Airflow
            return Airflow.from_config(config).get_one_schema(dag_name, schema)
        return jsonschema
