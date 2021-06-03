from .meta_model import EmptyModel
from ..shared.utils import db


class ApiViewModel(EmptyModel):
    """
    This model should contain all the views by name declared in the endpoints init
    """

    __tablename__ = "api_view"
    id = db.Column(db.Integer, db.Sequence("apiview_id_seq"), primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    url_rule = db.Column(db.String(128), nullable=False)

    def __eq__(self, other):
        return (isinstance(other, self.__class__)) and (self.name == other.name)

    def __neq__(self, other):
        return self.name != other.name

    def __repr__(self):
        return self.name

    @staticmethod
    def get_one_by_name(name):
        return ApiViewModel.query.filter_by(name=name).first()
