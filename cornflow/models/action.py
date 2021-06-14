"""

"""
from .meta_model import EmptyModel
from ..shared.utils import db


class ActionModel(EmptyModel):
    """
    This model contains the base actions over the REST API. These are:

    * can get
    * can patch
    * can post
    * can put
    * can delete
    """

    __tablename__ = "actions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), unique=True, nullable=False)

    def __repr__(self):
        return str(self.id) + ": " + self.name

    @staticmethod
    def get_all_objects():
        return ActionModel.query.all()
