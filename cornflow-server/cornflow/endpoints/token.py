# Import from libraries
from flask import request
from flask_apispec import marshal_with, doc

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.schemas.user import TokenEndpointResponse
from cornflow.shared.authentication import Auth
from cornflow.shared.const import ALL_DEFAULT_ROLES
from cornflow.shared.exceptions import InvalidCredentials, ObjectDoesNotExist


class TokenEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES

    def __init__(self):
        super().__init__()
        self.auth_class = Auth()

    @doc(description="Check token", tags=["Users"])
    @marshal_with(TokenEndpointResponse)
    def get(self):
        """
        API method to check if a token is valid.

        :return: A dictionary (containing the token and a boolean 'valid') and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        token = Auth().get_token_from_header(request.headers)
        try:
            self.get_user()
        except (InvalidCredentials, ObjectDoesNotExist):
            return {"token": token, "valid": 0}, 200
        return {"token": token, "valid": 1}, 200
