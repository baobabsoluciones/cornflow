"""

"""
# Import from libraries
from flask_apispec import marshal_with, doc

# Import from internal modules
from ..models import ApiViewModel
from ..schemas.apiview import ApiViewResponse
from ..shared.authentication import Auth
from ..shared.const import ADMIN_ROLE
from cornflow_core.authentication import authenticate
from cornflow_core.resources import BaseMetaResource


class ApiViewListEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]
    DESCRIPTION = (
        "Endpoint to get the list of all the endpoints defined in cornflow and its url"
    )

    def __init__(self):
        super().__init__()
        self.data_model = ApiViewModel

    @doc(description="Get all the api views", tags=["ApiViews"])
    @authenticate(auth_class=Auth())
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
        return self.get_list()
