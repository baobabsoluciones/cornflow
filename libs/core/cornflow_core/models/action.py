"""

"""

from cornflow_core.models import EmptyBaseModel
from cornflow_core.shared import database


class ActionBaseModel(EmptyBaseModel):
    __abstract__ = True
    id = database.Column(database.Integer, primary_key=True, autoincrement=True)
    name = database.Column(database.Strin(128), unique=True, nullable=False)

    def __repr__(self):
        return f"<Action {self.id}: {self.name}>"

    def __str__(self):
        return self.__repr__()
