"""
External endpoint for the user to signup
"""
# Import from libraries
from flask import request
from flask_restful import Resource

# Import from internal modules
from ..models import UserModel
from ..schemas import UserSchema
from ..shared.authentication import Auth

# Initialize the schema that the endpoint uses
user_schema = UserSchema()


class SignUpEndpoint(Resource):
    """
    Endpoint used to sign up to the cornflow web server.
    """
    def post(self):
        """
        API (POST) method tyo sign up to the cornflow webserver

        :return: A dictionary with a message (either an error during signup or the generated token for the user session)
        and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        req_data = request.get_json()
        data = user_schema.load(req_data)

        user_in_db = UserModel.get_one_user_by_email(data.get('email'))
        if user_in_db:
            message = {'error': 'email already in use, please supply another email address'}
            return message, 400

        user = UserModel(data)
        user.save()

        ser_data = user_schema.dump(user)

        token, error = Auth.generate_token(ser_data.get('id'))

        if error:
            return error, 400

        return {'token': token}, 201
