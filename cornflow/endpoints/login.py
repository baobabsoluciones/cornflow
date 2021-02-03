"""
External endpoint for the user to login to the cornflow webserver
"""
# Import from libraries
from flask import request
from flask_restful import Resource
from marshmallow.exceptions import ValidationError

# Import from internal modules
from ..models import UserModel
from ..schemas import UserSchema
from ..shared.authentication import Auth
from ..shared.exceptions import InvalidUsage, InvalidCredentials

# Initialize the schema that the endpoint uses
user_schema = UserSchema()


class LoginEndpoint(Resource):
    """
    Endpoint used to do the login to the cornflow webserver
    """
    def post(self):
        """
        API (POST) method to log in in to the web server.

        :return: A dictionary with a message (either an error during login or the generated token for the user session)
          and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        req_data = request.get_json()
        try:
            data = user_schema.load(req_data, partial=True)
        except ValidationError as val_err:
            raise InvalidUsage(error=str(val_err.normalized_messages()))

        if not data.get('email') or not data.get('password'):
            raise InvalidUsage(error='You need email and password to sign in')

        user = UserModel.get_one_user_by_email(data.get('email'))

        if not user:
            raise InvalidCredentials()

        if not user.check_hash(data.get('password')):
            raise InvalidCredentials()

        ser_data = user_schema.dump(user)
        user_id = ser_data.get('id')
        try:
            token = Auth.generate_token(user_id)
        except Exception as e:
            raise InvalidUsage(error='error in generating user token: ' + str(e), status_code=400)

        return {'token': token, 'id': user_id}, 200
