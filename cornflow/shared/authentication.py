import datetime
from functools import wraps

import jwt
from flask import request, g, current_app
from ..shared.exceptions import InvalidCredentials, ObjectDoesNotExist, NoPermission

from ..models.user import UserModel


class Auth:

    @staticmethod
    def generate_token(user_id):
        """

        :param user_id:
        :return:
        """
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
            'iat': datetime.datetime.utcnow(),
            'sub': user_id
        }

        return jwt.encode(payload, current_app.config['SECRET_KEY'], 'HS256').decode('utf8')

    @staticmethod
    def decode_token(token):
        """

        :param token:
        :return:
        """
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms='HS256')
            return {'user_id': payload['sub']}
        except jwt.ExpiredSignatureError:
            raise InvalidCredentials(error='Token expired, please login again', status_code=400)
        except jwt.InvalidTokenError:
            raise InvalidCredentials(error='Invalid token, please try again with a new token', status_code=400)

    @staticmethod
    def get_token_from_header(headers):
        if 'Authorization' not in headers:
            raise InvalidCredentials(error='Auth token is not available', status_code=400)
        auth_header = headers.get('Authorization')
        if not auth_header:
            return ''
        try:
            return auth_header.split(" ")[1]
        except Exception as e:
            raise InvalidCredentials(error='The Authorization header has a bad syntax: {}'.
                                     format(e))

    @staticmethod
    def get_user_obj_from_header(headers):
        """
        returns a user from the headers of the request

        :return: user
        :rtype: UserModel
        """
        token = Auth.get_token_from_header(headers)
        data = Auth.decode_token(token)
        user_id = data['user_id']
        user = UserModel.get_one_user(user_id)
        if not user:
            raise ObjectDoesNotExist("User does not exist, invalid token")
        return user

    # user decorator
    @staticmethod
    def auth_required(func):
        """
        Auth decorator
        :param func: 
        :return:
        """

        @wraps(func)
        def decorated_user(*args, **kwargs):
            user = Auth.get_user_obj_from_header(request.headers)
            g.user = {'id': user.id}
            return func(*args, **kwargs)

        return decorated_user

    # super admin decorator
    @staticmethod
    def super_admin_required(func):
        """
        Auth decorator that checks if user is super_admin
        :param func:
        :return:
        """

        @wraps(func)
        def decorated_super_admin(*args, **kwargs):
            user = Auth.get_user_obj_from_header(request.headers)
            if not user.super_admin:
                raise NoPermission(error='You do not have permission to access this endpoint')

            g.user = {'id': user.id}
            return func(*args, **kwargs)

        return decorated_super_admin

    @staticmethod
    def return_user_from_token(token):
        user_id = Auth.decode_token(token)['user_id']
        return user_id
