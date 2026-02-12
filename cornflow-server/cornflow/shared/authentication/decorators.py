"""
This file contains the decorator used for the authentication
"""

from functools import wraps
from .auth import Auth
from cornflow.shared.exceptions import InvalidCredentials
from flask import current_app


def authenticate(
    auth_class: Auth, optional_auth: str = None, no_auth_list: list = None
):
    """
    This is the decorator used for the authentication

    :param auth_class: the class used for the authentication. It should be `BaseAuth` or a class that inherits from it
    and that has a authenticate method.
    :param optional_auth: the env variable that indicates if authentication should be deactivated
    :param no_auth_list: the list of the values that indicates if authentication should be deactivated
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
            if endpoint_qualified_for_no_auth(no_auth_list, optional_auth):
                # Authentication is deactivated for this value
                return func(*args, **kwargs)

            if auth_class.authenticate():
                return func(*args, **kwargs)
            else:
                raise InvalidCredentials("Unable to authenticate the user")
        return wrapper

    return decorator

def endpoint_qualified_for_no_auth(no_auth_list, optional_auth):
    """
    This function is used to check if the endpoint is qualified for no authentication.

    :param no_auth_list: the list of the values that indicates if authentication should be deactivated
    :param optional_auth: the env variable that indicates if authentication should be deactivated
    :type no_auth_list: list
    :type optional_auth: str
    :return: True if the endpoint is qualified for no authentication, False otherwise
    """
    if optional_auth is None:
        return False
    if no_auth_list is None:
        raise InvalidCredentials(
            "The list of the values that indicates if authentication should be deactivated is not defined"
        )
    env_variable = current_app.config[optional_auth]
    if env_variable in no_auth_list:
        return True
    return False