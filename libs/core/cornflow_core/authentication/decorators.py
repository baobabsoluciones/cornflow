from functools import wraps
from .auth import BaseAuth
from cornflow_core.exceptions import InvalidCredentials


def authenticate(auth_class: BaseAuth):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if auth_class.authenticate():
                return func(*args, **kwargs)
            else:
                raise InvalidCredentials("Unable to authenticate the user")

        return wrapper

    return decorator
