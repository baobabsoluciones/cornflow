from flaskr.shared.resource import BaseResource
from flask import request
from flaskr.models.user import UserModel, UserSchema
from flaskr.shared.authentication import Auth

user_schema = UserSchema()


class UserEndpoint(BaseResource):

    @Auth.auth_required
    def get(self):
        users = UserModel.get_all_users()
        ser_users = user_schema.dump(users, many=True)
        print(ser_users)
        return ser_users, 200

    def post(self):
        """

        :return:
        """
        req_data = request.get_json()
        print(req_data)
        data = user_schema.load(req_data)

        user_in_db = UserModel.get_one_user_by_email(data.get('email'))
        print(user_in_db)
        if user_in_db:
            message = {'error':'User already exists, please supply another email address'}
            return message, 400

        user = UserModel(data)
        user.save()

        ser_data = user_schema.dump(user)

        token, error = Auth.generate_token(ser_data.get('id'))

        if error:
            return error, 400

        return {'token': token}, 201
