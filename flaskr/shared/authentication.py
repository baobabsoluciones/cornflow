import datetime
from functools import wraps

import jwt
from flask import Response, request, json, g, current_app

from ..models.user import UserModel


class Auth:

    @staticmethod
    def generate_token(user_id):
        """

        :param user_id:
        :return:
        """
        try:
            payload = {
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
                'iat': datetime.datetime.utcnow(),
                'sub': user_id
            }

            return jwt.encode(payload, current_app.config['SECRET_KEY'], 'HS256').decode('utf8'), None

        except Exception as e:
            return '', {'error': 'error in generating user token (' + str(e) + ' )'}

    @staticmethod
    def decode_token(token):
        """

        :param token:
        :return:
        """
        re = {'data': {}, 'error': {}}
        try:
            payload = jwt.decode(token, 'THISNEEDSTOBECHANGED', 'HS256')
            re['data'] = {'user_id': payload['sub']}
            return re
        except jwt.ExpiredSignatureError:
            re['error'] = {'message': 'token expired, please login again'}
            return re
        except jwt.InvalidTokenError:
            re['error'] = {'message': 'Invalid token, please try again with a new token'}
            return re

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
            if 'Authorization' not in request.headers:
                return Response(mimetype="application/json",
                                response=json.dumps({'error': 'Auth token is not available'}), status=400)
            auth_header = request.headers.get('Authorization')
            if auth_header:
                token = auth_header.split(" ")[1]
            else:
                token = ''
            data = Auth.decode_token(token)
            if data['error']:
                return Response(mimetype="application/json", response=json.dumps(data['error']), status=400)

            user_id = data['data']['user_id']
            check_user = UserModel.get_one_user(user_id)
            if not check_user:
                return Response(mimetype="application/json",
                                response=json.dumps({'error': 'User does not exist, invalid token'}))

            g.user = {'id': user_id}
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
            if 'Authorization' not in request.headers:
                return Response(mimetype="application/json",
                                response=json.dumps({'error': 'Auth token is not available'}), status=400)
            auth_header = request.headers.get('Authorization')
            if auth_header:
                token = auth_header.split(" ")[1]
            else:
                token = ''
            data = Auth.decode_token(token)
            if data['error']:
                return Response(mimetype="application/json", response=json.dumps(data['error']), status=400)

            user_id = data['data']['user_id']
            check_user = UserModel.get_one_user(user_id)
            if not check_user:
                return Response(mimetype="application/json",
                                response=json.dumps({'error': 'User does not exist, invalid token'}))

            if not check_user.super_admin:
                return Response(mimetype='application/json',
                                response=json.dumps({'error': 'You do not have permission to access this endpoint'}))

            g.user = {'id': user_id}
            return func(*args, **kwargs)

        return decorated_super_admin

    @staticmethod
    def return_user_info(req_data):
        token = req_data.headers.get('Authorization').split(" ")[1]
        user_id = Auth.decode_token(token)['data']['user_id']
        admin, super_admin = UserModel.get_user_info(user_id)
        return user_id, admin, super_admin
