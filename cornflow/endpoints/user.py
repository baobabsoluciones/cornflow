"""
Endpoints for the user profiles
"""
# Import from libraries
from flask_restful import Resource
from flask import request

# Import from internal modules
from ..models import UserModel
from ..schemas import UserSchema
from ..shared.authentication import Auth

# Initialize the schema that the endpoint uses
user_schema = UserSchema()


class UserEndpoint(Resource):
    """
    Endpoint with a get method which gives back all the info related to the users.
    Including their instances and executions
    """
    @Auth.super_admin_required
    def get(self):
        """
        API (GET) method to get all the info from all the users
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by the superuser

        :return: A dictionary with the user data and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        # TODO: maybe this method should be change in two ways:
        #  * Only give back the information of all users that belong to the same project / organization
        #  (not implemented yet) from the admin user demanding it.
        #  * Only give back the info of all users to the super_admin (us) to be able to perform sanity checks.
        users = UserModel.get_all_users()
        ser_users = user_schema.dump(users, many=True)
        return ser_users, 200


# TODO: the PUT method here could be used to change the password of the user.
#   These endpoints could be used mainly by the cornflow webserver UI.
class UserDetailsEndpoint(Resource):
    """
    Endpoint use to get the information of one single user
    """
    @Auth.auth_required
    def get(self, user_id):
        """

        :param str user_id: User ID.
        :return:
        :rtype: Tuple(dict, integer)
        """
        ath_user_id, admin, super_admin = Auth.return_user_info(request)
        if ath_user_id != user_id and not (admin or super_admin):
            return {}, 400
        user = UserModel.get_one_user(user_id)
        ser_users = user_schema.dump(user, many=False)
        return ser_users, 200
