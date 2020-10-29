"""
Endpoints for the user profiles
"""
from flask_restful import Resource

from ..models import UserModel, UserSchema
from ..shared import Auth

user_schema = UserSchema()


class UserEndpoint(Resource):
    """
    Endpoint with a get method which gives back all the info related to the users.
    Including their instances and executions
    """
    @Auth.auth_required
    def get(self):
        """
        
        """
        users = UserModel.get_all_users()
        ser_users = user_schema.dump(users, many=True)
        return ser_users, 200
