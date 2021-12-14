"""

"""
# Import from libraries
from sqlalchemy.dialects.postgresql import TEXT

# Import from internal modules
from .meta_model import TraceAttributes
from ..shared.utils import db


class DeployedDAG(TraceAttributes):
    """
    This model contains the registry of the DAGs that are deployed on the corresponding Airflow server
    """

    __tablename__ = "deployed_dags"
    id = db.Column(db.String(128), primary_key=True)
    description = db.Column(TEXT, nullable=True)

    def __init__(self, data):
        super().__init__()
        self.id = data.get("dag_id")
        self.description = data.get("description", None)

    def __repr__(self):
        return self.id
