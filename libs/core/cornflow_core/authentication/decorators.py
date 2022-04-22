from functools import wraps
from .auth import BaseAuth
from cornflow_core.exceptions import InvalidCredentials


def authenticate(auth_class: BaseAuth):
    """

    :param auth_class:
    :type auth_class:
    :return:
    :rtype:
    """

    def decorator(func):
        """

        :param func:
        :type func:
        :return:
        :rtype:
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            """

            :param args:
            :type args:
            :param kwargs:
            :type kwargs:
            :return:
            :rtype:
            """
            if auth_class.authenticate():
                return func(*args, **kwargs)
            else:
                raise InvalidCredentials("Unable to authenticate the user")

        return wrapper

    return decorator
