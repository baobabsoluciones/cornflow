"""

"""
from flask import request

from ..models import UserModel, UserSchema
from ..shared import Auth, BaseResource

user_schema = UserSchema()


class SingUpEndpoint(BaseResource):
    """

    """
    def post(self):
        """

        """
        req_data = request.get_json()
        data = user_schema.load(req_data)

        user_in_db = UserModel.get_one_user_by_email(data.get('email'))
        if user_in_db:
            message = {'error': 'User already exists, please supply another email address'}
            return message, 400

        user = UserModel(data)
        user.save()

        ser_data = user_schema.dump(user)

        token, error = Auth.generate_token(ser_data.get('id'))

        if error:
            return error, 400

        return {'token': token}, 201
