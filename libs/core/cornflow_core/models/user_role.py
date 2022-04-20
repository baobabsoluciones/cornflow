"""

"""

from cornflow_core.models import TraceAttributesModel
from cornflow_core.shared import db


class UserRoleBaseModel(TraceAttributesModel):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    @classmethod
    def del_one_user(cls, user_id):
        """
        Method to delete all the assigned roles to one user

        :param int user_id: the ID of the user
        :return: a list with all the deleted objects.
        :rtype: list
        """
        return cls.query.filter_by(user_id=user_id).delete(synchronize_session=False)
