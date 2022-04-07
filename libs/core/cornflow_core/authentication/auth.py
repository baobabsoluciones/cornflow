from jwt import decode, encode, ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timedelta
from flask import current_app, g, request
from cornflow_core.exceptions import (
    InvalidCredentials,
    InvalidUsage,
    ObjectDoesNotExist,
)
from typing import Dict
from functools import wraps
from werkzeug.datastructures import Headers

from cornflow_core.models import UserBaseModel


class Auth:
    """ """

    user_model = UserBaseModel

    @staticmethod
    def generate_token(user_id: int = None) -> str:
        """
        Generates a token given a user_id with a duration of one day

        :param int user_id: user code to be encoded in the token to identify the user afterwards
        :return: the generated token
        :rtype: str
        """
        if user_id is None:
            raise InvalidUsage("The user id passed to generate the token is not valid.")

        payload = {
            "exp": datetime.utcnow() + timedelta(days=1),
            "iat": datetime.utcnow(),
            "sub": user_id,
        }

        return encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")

    @staticmethod
    def decode_token(token: str = None) -> Dict:
        """

        :param str token:
        :return:
        :rtype:
        """
        if token is None:
            raise InvalidUsage("The provided token is not valid")
        try:
            payload = decode(
                token, current_app.config["SECRET_KEY"], algorithms="HS256"
            )
            return {"user_id": payload["sub"]}
        except ExpiredSignatureError:
            raise InvalidCredentials("The token has expired, please login again")
        except InvalidTokenError:
            raise InvalidCredentials("Invalid token, please try again with a new token")

    @staticmethod
    def get_token_from_header(headers: Headers = None) -> str:
        """

        :param headers:
        :type headers: `Headers`
        :return:
        :rtype:
        """
        if headers is None:
            raise InvalidUsage

        if "Authorization" not in headers:
            raise InvalidCredentials("Auth token is not available")
        auth_header = headers.get("Authorization")
        if not auth_header:
            return ""
        try:
            return auth_header.split(" ")[1]
        except Exception as e:
            raise InvalidCredentials(f"The authorization header has a bad syntax: {e}")

    @classmethod
    def get_user_from_header(cls, headers: Headers = None) -> UserBaseModel:
        """

        :param headers:
        :type headers: `Headers`
        :return:
        :rtype:
        """
        if headers is None:
            raise InvalidUsage()
        token = cls.get_token_from_header(headers)
        data = cls.decode_token(token)
        user_id = data["user_id"]
        user = cls.user_model.get_one_user(user_id)
        if user is None:
            raise ObjectDoesNotExist("User does not exist, invalid token")
        return user

    @staticmethod
    def auth_decorator(auth: bool = True):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                print(f"AUTH auth required: {auth}")
                if auth:
                    user = Auth.get_user_from_header(request.headers)
                    g.user = {"id": user.id}
                return func(*args, **kwargs)

            return wrapper

        return decorator
