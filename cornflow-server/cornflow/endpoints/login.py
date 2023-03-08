"""
External endpoint for the user to login to the cornflow webserver
"""

# Full import from libraries
from cornflow_core.resources import LoginBaseEndpoint

# Partial imports
from flask import current_app
from flask_apispec import use_kwargs, doc

# Import from internal modules
from cornflow.models import PermissionsDAG, UserModel, UserRoleModel
from cornflow_core.schemas import LoginEndpointRequest, LoginOpenAuthRequest
from cornflow.shared.authentication import Auth


class LoginEndpoint(LoginBaseEndpoint):
    """
    Endpoint used to do the login to the cornflow webserver
    """

    def __init__(self):
        super().__init__()
        self.data_model = UserModel
        self.auth_class = Auth
        self.user_role_association = UserRoleModel

    @doc(description="Log in", tags=["Users"])
    @use_kwargs(LoginEndpointRequest, location="json")
    def post(self, **kwargs):
        """
        API (POST) method to log in in to the web server.

        :return: A dictionary with a message (either an error during login or the generated token for the user session)
          and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """

        content, status = self.log_in(**kwargs)
        if int(current_app.config["OPEN_DEPLOYMENT"]) == 1:
            PermissionsDAG.delete_all_permissions_from_user(content["id"])
            PermissionsDAG.add_all_permissions_to_user(content["id"])
        return content, status


class LoginOpenAuthEndpoint(LoginBaseEndpoint):
    """ """

    def __init__(self):
        super().__init__()
        self.data_model = UserModel
        self.auth_class = Auth
        self.user_role_association = UserRoleModel

    @doc(description="Log in", tags=["Users"])
    @use_kwargs(LoginOpenAuthRequest, location="json")
    def post(self, **kwargs):
        """ """

        content, status = self.log_in(**kwargs)
        if int(current_app.config["OPEN_DEPLOYMENT"]) == 1:
            PermissionsDAG.delete_all_permissions_from_user(content["id"])
            PermissionsDAG.add_all_permissions_to_user(content["id"])
        return content, status
