"""
External endpoint for the user to login to the cornflow webserver
"""
# Import from libraries
from flask import request
from flask_restful import Resource

# Import from internal modules
from ..models import UserModel
from ..schemas import UserSchema
from ..shared import Auth

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

        data = user_schema.load(req_data, partial=True)

        if not data.get('email') or not data.get('password'):
            return {'error': 'you need email and password to sign in'}, 400

        user = UserModel.get_one_user_by_email(data.get('email'))

        if not user:
            return {'error': 'email not recognized, please check'}, 400

        if not user.check_hash(data.get('password')):
            return {'error': 'password invalid'}, 400

        ser_data = user_schema.dump(user)

        token, error = Auth.generate_token(ser_data.get('id'))

        return {'token': token}, 200
