"""

"""

from flask_apispec import marshal_with, doc

# Import from internal modules
from ..models import ActionModel
from ..schemas.action import ActionsResponse
from ..shared.authentication import Auth
from cornflow_core.authentication import authenticate
from ..shared.const import ADMIN_ROLE
from cornflow_core.resources import BaseMetaResource


class ActionListEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]
    DESCRIPTION = "Endpoint which allows to get the actions defined in the application"

    def __init__(self):
        super().__init__()
        self.data_model = ActionModel

    @doc(description="Get all the actions", tags=["Actions"])
    @authenticate(auth_class=Auth())
    @marshal_with(ActionsResponse(many=True))
    def get(self):
        """
        API method to get the actions defined in the application.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :return: A dictionary with the response (data of the actions or an error message)
        and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return self.get_list()
