"""

"""
# Imports from external libraries
from flask_apispec import marshal_with, doc
from flask import current_app

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import ActionModel
from cornflow.schemas.action import ActionsResponse
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import ADMIN_ROLE


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
        current_app.logger.info(f"User {self.get_user()} gets all actions")
        return self.get_list()
