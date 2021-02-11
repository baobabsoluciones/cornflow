"""
External endpoint for the user to login to the cornflow webserver
"""
# Import from libraries
from flask_restful import Resource
from flask_apispec.views import MethodResource
from flask_apispec import use_kwargs, doc

# Import from internal modules
from ..models import UserModel
from ..schemas.user import UserSchema, LoginEndpointRequest
from ..shared.authentication import Auth
from ..shared.exceptions import InvalidUsage, InvalidCredentials

# Initialize the schema that the endpoint uses
user_schema = UserSchema()


class LoginEndpoint(Resource, MethodResource):
    """
    Endpoint used to do the login to the cornflow webserver
    """

    @doc(description='Log in', tags=['Users'])
    @use_kwargs(LoginEndpointRequest, location='json')
    def post(self, **kwargs):
        """
        API (POST) method to log in in to the web server.

        :return: A dictionary with a message (either an error during login or the generated token for the user session)
          and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """

        user = UserModel.get_one_user_by_email(kwargs.get('email'))

        if not user:
            raise InvalidCredentials()

        if not user.check_hash(kwargs.get('password')):
            raise InvalidCredentials()

        try:
            token = Auth.generate_token(user.id)
        except Exception as e:
            raise InvalidUsage(error='error in generating user token: ' + str(e), status_code=400)

        return {'token': token, 'id': user.id}, 200
