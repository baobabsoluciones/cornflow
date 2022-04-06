"""

"""
from sqlalchemy.dialects.postgresql import TEXT

from cornflow_core.models import EmptyBaseModel
from cornflow_core.shared import database


class ViewBaseModel(EmptyBaseModel):
    __abstract__ = True
    id = database.Column(database.Integer, primary_key=True, autoincrement=True)
    name = database.Column(database.Strin(128), unique=True, nullable=False)
    url_rule = database.Column(database.String(128), nullable=False)
    description = database.Column(TEXT, nullable=True)

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
