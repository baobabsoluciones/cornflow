import datetime
from flask import request, g, current_app
from functools import wraps
import jwt

from ..models import ApiViewModel, UserModel, UserRoleModel, PermissionViewRoleModel
from ..shared.const import PERMISSION_METHOD_MAP
from ..shared.exceptions import InvalidCredentials, ObjectDoesNotExist, NoPermission


class Auth:
    @staticmethod
    def generate_token(user_id):
        """

        :param user_id:
        :return:
        """
        payload = {
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1),
            "iat": datetime.datetime.utcnow(),
            "sub": user_id,
        }

        return jwt.encode(payload, current_app.config["SECRET_KEY"], "HS256").decode(
            "utf8"
        )

    @staticmethod
    def decode_token(token):
        """

        :param token:
        :return:
        """
        try:
            payload = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms="HS256"
            )
            return {"user_id": payload["sub"]}
        except jwt.ExpiredSignatureError:
            raise InvalidCredentials(
                error="Token expired, please login again", status_code=400
            )
        except jwt.InvalidTokenError:
            raise InvalidCredentials(
                error="Invalid token, please try again with a new token",
                status_code=400,
            )

    @staticmethod
    def get_token_from_header(headers):
        if "Authorization" not in headers:
            raise InvalidCredentials(
                error="Auth token is not available", status_code=400
            )
        auth_header = headers.get("Authorization")
        if not auth_header:
            return ""
        try:
            return auth_header.split(" ")[1]
        except Exception as e:
            raise InvalidCredentials(
                error="The Authorization header has a bad syntax: {}".format(e)
            )

    @staticmethod
    def get_request_info(req):
        return getattr(req, "environ")["REQUEST_METHOD"], getattr(req, "url_rule").rule

    @staticmethod
    def get_user_obj_from_header(headers):
        """
        returns a user from the headers of the request

        :return: user
        :rtype: UserModel
        """
        token = Auth.get_token_from_header(headers)
        data = Auth.decode_token(token)
        user_id = data["user_id"]
        user = UserModel.get_one_user(user_id)
        if user is None:
            raise ObjectDoesNotExist("User does not exist, invalid token")
        return user

    @staticmethod
    def get_permission_for_request(req, user_id):
        method, url = Auth.get_request_info(req)
        user_role = UserRoleModel.get_one_user(user_id=user_id)
        if user_role is None:
            raise NoPermission("You do not have permission to access this endpoint")

        action_id = PERMISSION_METHOD_MAP[method]
        view_id = ApiViewModel.query.filter_by(url_rule=url).first().id

        for role in user_role:
            has_permission = PermissionViewRoleModel.get_permission(
                role.role_id, view_id, action_id
            )

            if has_permission:
                return True

        raise NoPermission("You do not have permission to access this endpoint")

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
            Auth.get_permission_for_request(request, user.id)
            g.user = {"id": user.id}
            return func(*args, **kwargs)

        return decorated_user

    @staticmethod
    def return_user_from_token(token):
        user_id = Auth.decode_token(token)["user_id"]
        return user_id
