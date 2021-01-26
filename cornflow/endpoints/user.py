"""
Endpoints for the user profiles
"""
# Import from libraries
from flask_restful import Resource, fields, marshal_with, marshal
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
    resource_fields = dict(
        id=fields.Integer,
        admin=fields.Boolean,
        super_admin=fields.Boolean,
        name=fields.String,
        email=fields.String,
        created_at=fields.String
    )

    @Auth.super_admin_required
    @marshal_with(resource_fields)
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
    resource_fields = dict(
        name=fields.String,
        email=fields.String
    )

    @Auth.auth_required
    def get(self, user_email):
        """

        :param str user_email: User email.
        :return:
        :rtype: Tuple(dict, integer)
        """
        ath_user_id, admin, super_admin = Auth.return_user_info(request)
        ath_user_obj = UserModel.get_one_user(ath_user_id)
        if ath_user_obj.email != user_email and not (admin or super_admin):
            return {'error': 'You have no permission to access given user'}, 400
        user_obj = UserModel.get_one_user_by_email(user_email)
        ser_users = user_schema.dump(user_obj, many=False)
        return marshal(ser_users, self.resource_fields), 200

    @Auth.auth_required
    def delete(self, user_email):
        """

        :param str user_email: User email.
        :return:
        :rtype: Tuple(dict, integer)
        """
        ath_user_id, admin, super_admin = Auth.return_user_info(request)
        ath_user_obj = UserModel.get_one_user(ath_user_id)
        if ath_user_obj.email != user_email and not (admin or super_admin):
            return {'error': 'You have no permission to access given user'}, 400
        user_obj = UserModel.get_one_user_by_email(user_email)
        user_obj.delete()
        return {'message': 'The object has been deleted'}, 200

    @Auth.auth_required
    def put(self, user_email):
        """
        API method to edit an existing user.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user. Only admin and superadmin can edit other users.

        :param str user_email: email of the user
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        ath_user_id, admin, super_admin = Auth.return_user_info(request)
        ath_user_obj = UserModel.get_one_user(ath_user_id)
        if ath_user_obj.email != user_email and not (admin or super_admin):
            return {'error': 'You have no permission to access given user'}, 400
        user_obj = UserModel.get_one_user_by_email(user_email)
        request_data = request.get_json()
        data = self.schema.load(request_data, partial=True)
        user_obj.update(data)
        user_obj.save()
        return user_obj, 201

class ToggleUserAdmin(Resource):

    @Auth.super_admin_required
    def put(self, user_email, make_admin):
        """
        API method to make admin or take out privileges.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user. Only superadmin can change this.

        :param str user_email: email of the user
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        user_obj = UserModel.get_one_user_by_email(user_email)
        if make_admin:
            user_obj.admin = 1
        else:
            user_obj.admin = 0
        user_obj.save()
        return_keys = ['name', 'email', 'admin']
        return {k: getattr(user_obj, k) for k in return_keys}, 201
