"""
This file contains the decorator used for the authentication
"""
from functools import wraps
from .auth import BaseAuth
from cornflow_core.exceptions import InvalidCredentials


def authenticate(auth_class: BaseAuth):
    """
    This is the decorator used for the authentication

    :param auth_class: the class used for the authentication. It should be `BaseAuth` or a class that inherits from it
    and that has a authenticate method.
    :type auth_class: `BaseAuth`
    :return: the wrapped function
    """

    def decorator(func: callable):
        """
        The decorator definition

        :param callable func: the function that gets decorated
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            """
            The wrapper to the function that performs the authentication.

            :param args: the original args sent to the decorated function
            :param kwargs: the original kwargs sent to the decorated function
            :return: the result of the call to the function
            """
            if auth_class.authenticate():
                return func(*args, **kwargs)
            else:
                raise InvalidCredentials("Unable to authenticate the user")

        return wrapper

    return decorator
