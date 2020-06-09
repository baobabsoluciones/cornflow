from flask_restful import Resource
from flask import request
from flaskr.models.user import UserSchema, UserModel
from flaskr.shared.authentication import Auth

user_schema = UserSchema()

class LoginEndpoint(Resource):

    def post(self):
        req_data = request.get_json()

        data = user_schema.load(req_data, partial=True)

        if not data.get('email') or not data.get('password'):
            return {'error': 'you need email and password to sign in'}, 400

        user = UserModel.get_one_user_by_email(data.get('email'))

        if not user:
            return {'error': 'invalid credentials'}, 400

        if not user.check_hash(data.get('password')):
            return {'error': 'invalid credentials'}, 400

        ser_data = user_schema.dump(user)
        print(ser_data)

        token, error = Auth.generate_token(ser_data.get('id'))

        return {'token': token}, 200