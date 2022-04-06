"""

"""
# Import from libraries
from sqlalchemy.dialects.postgresql import TEXT

from cornflow_core.models import ViewBaseModel

# Import from internal modules
# from .meta_model import EmptyModel
from ..shared.utils import db


class ApiViewModel(ViewBaseModel):
    """
    This model should contain all the views by name declared in the endpoints init
    """

    __tablename__ = "api_view"

    permissions = db.relationship(
        "PermissionViewRoleModel",
        backref="api_views",
        lazy=True,
        primaryjoin="and_(ApiViewModel.id==PermissionViewRoleModel.api_view_id, "
        "PermissionViewRoleModel.deleted_at==None)",
        cascade="all,delete",
    )
