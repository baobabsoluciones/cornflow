# Imports from libraries
from flask_apispec import doc, marshal_with, use_kwargs

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import MainAlarmsModel
from cornflow.schemas.main_alarms import (
    MainAlarmsResponse,
    MainAlarmsPostRequest,
    QueryFiltersMainAlarms
)
from cornflow.shared.authentication import Auth, authenticate


class MainAlarmsEndpoint(BaseMetaResource):
    """
    Endpoint used to manage the table main_alarms.
    Available methods: [get, post]
    """

    def __init__(self):
        super().__init__()
        self.data_model = MainAlarmsModel
        self.unique = ["id"]

    @doc(
        description="Get list of all the elements in the table",
        tags=["None"],
    )
    @authenticate(auth_class=Auth())
    @marshal_with(MainAlarmsResponse(many=True))
    @use_kwargs(QueryFiltersMainAlarms, location="query")
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
    @authenticate(auth_class=Auth())
    @marshal_with(MainAlarmsResponse)
    @use_kwargs(MainAlarmsPostRequest, location="json")
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