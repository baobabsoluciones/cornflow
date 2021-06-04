"""

"""
# Import from libraries
from flask_apispec import marshal_with, doc
from flask_apispec.views import MethodResource

# Import from internal modules
from .meta_resource import MetaResource
from ..models import ApiViewModel
from ..schemas.apiview import ApiViewResponse
from ..shared.authentication import Auth
from ..shared.const import ADMIN_ROLE, SERVICE_ROLE


class ApiViewListEndpoint(MetaResource, MethodResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE, SERVICE_ROLE]
    DESCRIPTION = (
        "Endpoint to get the list of all the endpoints defined in cornflow and its url"
    )

    def __init__(self):
        super().__init__()
        self.model = ApiViewModel
        self.query = ApiViewModel.get_all_objects
        self.primary_key = "id"

    @doc(description="Get all the api views", tags=["ApiViews"])
    @Auth.auth_required
    @marshal_with(ApiViewResponse(many=True))
    def get(self):
        """
        API method to get the api views defined in cornflow.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :return: A dictionary with the response (data of the apiviews or an error message)
        and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return ApiViewModel.get_all_objects()
