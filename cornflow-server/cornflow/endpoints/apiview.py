"""

"""
from cornflow_core.authentication import authenticate

# Import from internal modules
from cornflow_core.models import ViewBaseModel
from cornflow_core.resources import BaseMetaResource
from cornflow_core.schemas import ViewResponse

# Import from libraries
from flask_apispec import marshal_with, doc
from flask import current_app

from cornflow.shared.authentication import Auth
from cornflow.shared.const import ADMIN_ROLE


class ApiViewListEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]
    DESCRIPTION = (
        "Endpoint to get the list of all the endpoints defined in cornflow and its url"
    )

    def __init__(self):
        super().__init__()
        self.data_model = ViewBaseModel

    @doc(description="Get all the api views", tags=["ApiViews"])
    @authenticate(auth_class=Auth())
    @marshal_with(ViewResponse(many=True))
    def get(self):
        """
        API method to get the api views defined in cornflow.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :return: A dictionary with the response (data of the apiviews or an error message)
        and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        current_app.logger.info(f"User {self.get_user()} gets all cases")
        return self.get_list()
