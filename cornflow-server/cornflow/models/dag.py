"""

"""
# Import from libraries
from sqlalchemy.dialects.postgresql import TEXT

# Import from internal modules
from cornflow_core.models import TraceAttributesModel
from cornflow_core.shared import db


class DeployedDAG(TraceAttributesModel):
    """
    This model contains the registry of the DAGs that are deployed on the corresponding Airflow server
    """

    __tablename__ = "deployed_dags"
    id = db.Column(db.String(128), primary_key=True)
    description = db.Column(TEXT, nullable=True)

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

    def __repr__(self):
        return f"<DAG {self.id}>"
