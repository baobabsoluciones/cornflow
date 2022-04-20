"""

"""
from sqlalchemy.dialects.postgresql import TEXT

from cornflow_core.models import EmptyBaseModel
from cornflow_core.shared import db


class ViewBaseModel(EmptyBaseModel):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    url_rule = db.Column(db.String(128), nullable=False)
    description = db.Column(TEXT, nullable=True)

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
    def get_one_by_name(cls, name):
        return cls.query.filter_by(name=name).first()
