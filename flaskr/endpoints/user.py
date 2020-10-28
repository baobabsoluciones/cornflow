"""
Endpoints for the user profiles
"""
from ..models import UserModel, UserSchema
from ..shared.authentication import Auth
from ..shared.resource import BaseResource

user_schema = UserSchema()


class UserEndpoint(BaseResource):
    """
    Endpoint with a get method which gives back all the info related to the users.
    Including their instances and executions
    """
    @Auth.auth_required
    def get(self):
        users = UserModel.get_all_users()
        ser_users = user_schema.dump(users, many=True)
        return ser_users, 200
