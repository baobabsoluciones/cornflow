from flask import request
from flask_restful import Resource
from marshmallow.exceptions import ValidationError

from ..models.user import UserModel
from ..schemas.user import UserSchema
from ..shared.authentication import Auth

user_schema = UserSchema()


class LoginEndpoint(Resource):

    def post(self):
        req_data = request.get_json()

        try:
            data = user_schema.load(req_data, partial=True)
        except ValidationError as val_err:
            return {'error': val_err.normalized_messages()}, 400

        if not data.get('email') or not data.get('password'):
            return {'error': 'You need email and password to sign in.'}, 400

        user = UserModel.get_one_user_by_email(data.get('email'))

        if not user:
            return {'error': 'Invalid credentials.'}, 400

        if not user.check_hash(data.get('password')):
            return {'error': 'Invalid credentials.'}, 400

        ser_data = user_schema.dump(user)

        token, error = Auth.generate_token(ser_data.get('id'))

        return {'token': token}, 200