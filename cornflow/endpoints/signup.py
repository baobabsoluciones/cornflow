"""
External endpoint for the user to signup
"""
# Import from libraries
from flask_restful import Resource
from flask_apispec.views import MethodResource
from flask_apispec import use_kwargs, doc

# Import from internal modules
from ..models import UserModel
from ..schemas.user import UserSignupRequest
from ..shared.authentication import Auth
from ..shared.exceptions import InvalidUsage, ObjectDoesNotExist, NoPermission, InvalidCredentials


class SignUpEndpoint(Resource, MethodResource):
    """
    Endpoint used to sign up to the cornflow web server.
    """

    @doc(description='Sign up', tags=['Users'])
    @use_kwargs(UserSignupRequest, location='json')
    def post(self, **kwargs):
        """
        API (POST) method to sign up to the cornflow webserver

        :return: A dictionary with a message (either an error during signup or the generated token for the user session)
          and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        user_in_db = UserModel.get_one_user_by_email(kwargs.get('email'))
        if user_in_db:
            raise InvalidCredentials(error='Email already in use, please supply another email address')

        user = UserModel(kwargs)
        user.save()

        try:
            token = Auth.generate_token(user.id)
        except Exception as e:
            raise InvalidUsage(error='Error in generating user token: ' + str(e), status_code=400)

        return {'token': token}, 201
