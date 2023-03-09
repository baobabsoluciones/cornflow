# Imports from libraries
from flask_apispec import doc, marshal_with, use_kwargs
from cornflow_core.authentication import authenticate, BaseAuth
from cornflow_core.resources import BaseMetaResource

from cornflow_core.constants import VIEWER_ROLE, PLANNER_ROLE, ADMIN_ROLE, SERVICE_ROLE

# Import from internal modules
from ..models import AlarmsModel
from ..schemas import (
    AlarmsResponse,
    AlarmsEditRequest,
    AlarmsPostRequest,
    AlarmsPostBulkRequest,
    AlarmsPutBulkRequest,
)


class AlarmsEndpoint(BaseMetaResource):
    """
    Endpoint used to manage the table alarms.

    Available methods: [get, post]
    """

    ROLES_WITH_ACCESS = [VIEWER_ROLE, PLANNER_ROLE, ADMIN_ROLE, SERVICE_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = AlarmsModel
        self.unique = ["id"]

    @doc(
        description="Get list of all the elements in the table",
        tags=["None"],
    )
    @authenticate(auth_class=BaseAuth())
    @marshal_with(AlarmsResponse(many=True))
    def get(self, **kwargs):
        """
        API method to get all the rows of the table.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :return: A list of objects with the data, and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return self.get_list(**kwargs)

    @doc(
        description="Add a new row to the table",
        tags=["None"],
    )
    @authenticate(auth_class=BaseAuth())
    @marshal_with(AlarmsResponse)
    @use_kwargs(AlarmsPostRequest, location="json")
    def post(self, **kwargs):
        """
        API method to add a row to the table.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :return: An object with the data for the created row,
        and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return self.post_list(data=kwargs)
