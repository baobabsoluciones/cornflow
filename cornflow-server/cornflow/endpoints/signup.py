"""
External endpoint for the user to signup
"""
# Import from libraries
from cornflow_core.resources import SignupBaseEndpoint
from flask import current_app
from flask_apispec import use_kwargs, doc

# Import from internal modules
from ..models import PermissionsDAG, UserRoleModel, UserModel
from cornflow_core.schemas import SignupRequest
from ..shared.authentication import Auth


class SignUpEndpoint(SignupBaseEndpoint):
    """
    Endpoint used to sign up to the cornflow web server.
    """

    def __init__(self):
        super().__init__()
        self.data_model = UserModel
        self.auth_class = Auth
        self.user_role_association = UserRoleModel

    @doc(description="Sign up", tags=["Users"])
    @use_kwargs(SignupRequest, location="json")
    def post(self, **kwargs):
        """
        API (POST) method to sign up to the cornflow webserver

        :return: A dictionary with a message (either an error during signup or the generated token for the user session)
          and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        content, status = self.sign_up(**kwargs)

        if int(current_app.config["OPEN_DEPLOYMENT"]) == 1:
            PermissionsDAG.add_all_permissions_to_user(content["id"])

        return content, status
