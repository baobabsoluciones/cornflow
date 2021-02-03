"""
External endpoint for the user to signup
"""
# Import from libraries
from flask import request
from flask_restful import Resource
from marshmallow.exceptions import ValidationError

# Import from internal modules
from ..models import UserModel
from ..schemas import UserSchema
from ..shared.authentication import Auth
from ..shared.exceptions import InvalidUsage, ObjectDoesNotExist, NoPermission, InvalidCredentials

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
        try:
            data = user_schema.load(req_data)
        except ValidationError as val_err:
            raise InvalidUsage(error=str(val_err.normalized_messages()))

        user_in_db = UserModel.get_one_user_by_email(data.get('email'))
        if user_in_db:
            raise InvalidCredentials(error='Email already in use, please supply another email address')

        user = UserModel(data)
        user.save()

        ser_data = user_schema.dump(user)

        try:
            token = Auth.generate_token(ser_data.get('id'))
        except Exception as e:
            raise InvalidUsage(error='Error in generating user token: ' + str(e), status_code=400)

        return {'token': token}, 201
