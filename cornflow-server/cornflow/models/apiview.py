"""

"""
# Import from libraries
from sqlalchemy.dialects.postgresql import TEXT

from cornflow_core.models import EmptyBaseModel

# Import from internal modules
# from .meta_model import EmptyModel
from ..shared.utils import db


class ApiViewModel(EmptyBaseModel):
    """
    This model should contain all the views by name declared in the endpoints init
    """

    __tablename__ = "api_view"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    url_rule = db.Column(db.String(128), nullable=False)
    description = db.Column(TEXT, nullable=True)

    permissions = db.relationship(
        "PermissionViewRoleModel",
        backref="api_views",
        lazy=True,
        primaryjoin="and_(ApiViewModel.id==PermissionViewRoleModel.api_view_id, "
        "PermissionViewRoleModel.deleted_at==None)",
        cascade="all,delete",
    )

    def __init__(self, data):
        super().__init__()
        self.name = data.get("name")
        self.url_rule = data.get("url_rule")
        self.description = data.get("description")

    def __eq__(self, other):
        return (isinstance(other, self.__class__)) and (self.name == other.name)

    def __neq__(self, other):
        return self.name != other.name

    def __repr__(self):
        return self.name

    @classmethod
    def get_one_by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    @classmethod
    def get_all_objects(cls):
        return cls.query.all()
