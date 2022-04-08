from functools import wraps
from .auth import Auth
from cornflow_core.exceptions import InvalidCredentials
from flask import request


def authenticate(auth_class: Auth):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"REQUEST: {request}")
            print(f"REQUEST HEADERS: {request.headers}")
            if auth_class.authenticate():
                return func(*args, **kwargs)
            else:
                raise InvalidCredentials("Unable to authenticate the user")

        return wrapper

    return decorator
