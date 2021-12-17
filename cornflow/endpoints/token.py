# Import from libraries
from flask import request
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, doc

# Import from internal modules
from .meta_resource import MetaResource
from ..schemas.user import TokenEndpointResponse
from ..shared.exceptions import InvalidCredentials, ObjectDoesNotExist
from ..shared.authentication import Auth


class TokenEndpoint(MetaResource, MethodResource):
    @doc(description="Check token", tags=["Users"])
    @marshal_with(TokenEndpointResponse)
    def get(self):
        """
        API method to check if a token is valid.

        :return: A dictionary (containing the token and a boolean 'valid') and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        token = Auth.get_token_from_header(request.headers)
        try:
            Auth.get_user_obj_from_header(request.headers)
        except (InvalidCredentials, ObjectDoesNotExist):
            return {"token": token, "valid": 0}, 200
        return {"token": token, "valid": 1}, 200
