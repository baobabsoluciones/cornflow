"""
This file contains the view model
"""

from sqlalchemy.dialects.postgresql import TEXT

from cornflow_core.models import EmptyBaseModel
from cornflow_core.shared import db


class ViewBaseModel(EmptyBaseModel):
    """
    This model stores the views / endpoints / resources of the API
    This model inherits from :class:`EmptyBaseModel` so it has no traceability

    The fields of the model are:

    - **id**: int, the primary key of the table, an integer value that is auto incremented
    - **name**: str, the name of the view
    - **url_rule**: str, the rule for the url
    - **description**: the description of the view
    """

    __tablename__ = "api_view"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    url_rule = db.Column(db.String(128), nullable=False)
    description = db.Column(TEXT, nullable=True)

    permissions = db.relationship(
        "PermissionViewRoleBaseModel",
        backref="api_views",
        lazy=True,
        primaryjoin="and_(ViewBaseModel.id==PermissionViewRoleBaseModel.api_view_id, "
        "PermissionViewRoleBaseModel.deleted_at==None)",
        cascade="all,delete",
    )

    def __init__(self, data):
        super().__init__()
        self.name = data.get("name")
        self.url_rule = data.get("url_rule")
        self.description = data.get("description")

    def __eq__(self, other):
        return (isinstance(other, self.__class__)) and (self.name == other.name)

    def __repr__(self):
        return f"<View {self.name}>"

    def __str__(self):
        return self.__repr__()

    @classmethod
    def get_one_by_name(cls, name: str):
        """
        This methods queries the model to search for a view with a given name.

        :param str name: The name that the view has
        :return: The found result, either an object :class:`ViewBaseModel` or None
        :rtype: None or :class:`ViewBaseModel`
        """
        return cls.query.filter_by(name=name).first()
