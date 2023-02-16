"""
a
"""
from cornflow_core.models import UserRoleBaseModel
from cornflow_core.shared import db

from cornflow.shared.const import ADMIN_ROLE, SERVICE_ROLE


class UserRoleModel(UserRoleBaseModel):
    """
    Model for the relationship between user and roles
    """

    # TODO: Should have a user_id to store the user that defined the assignation?
    __tablename__ = "user_role"
    __table_args__ = ({"extend_existing": True},)

    user = db.relationship("UserBaseModel", viewonly=True, lazy=False)
    role = db.relationship("RoleBaseModel", viewonly=True, lazy=False)

    @classmethod
    def is_admin(cls, user_id):
        """
        Method that checks if a given user has the admin role assigned

        :param int user_id: the ID of the user
        :return: a boolean indicating if the user has the admin role assigned or not
        :rtype: boolean
        """
        user_roles = cls.get_all_objects(user_id=user_id)
        for role in user_roles:
            if role.role_id == ADMIN_ROLE:
                return True

        return False

    @classmethod
    def is_service_user(cls, user_id):
        """
        Method that checks if a given user has the service role assigned

        :param int user_id: the ID of the user
        :return: a boolean indicating if the user has the service role assigned or not
        :rtype: boolean
        """
        user_roles = cls.get_all_objects(user_id=user_id).all()
        for role in user_roles:
            if role.role_id == SERVICE_ROLE:
                return True

        return False
