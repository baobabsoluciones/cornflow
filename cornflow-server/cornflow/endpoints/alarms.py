# Imports from libraries
from flask import current_app
from flask_apispec import doc, marshal_with, use_kwargs

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import AlarmsModel
from cornflow.schemas.alarms import (
    AlarmsResponse,
    AlarmsPostRequest,
    QueryFiltersAlarms
)
from cornflow.shared.authentication import Auth, authenticate


class AlarmsEndpoint(BaseMetaResource):
    """
    Endpoint used to manage the table alarms.
    Available methods: [get, post]
    """

    def __init__(self):
        super().__init__()
        self.data_model = AlarmsModel
        self.unique = ["id"]

    @doc(
        description="Get list of all the elements in the table",
        tags=["None"],
    )
    @authenticate(auth_class=Auth())
    @marshal_with(AlarmsResponse(many=True))
    @use_kwargs(QueryFiltersAlarms, location="query")
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


class AlarmDetailEndpoint(BaseMetaResource):
    """
    Endpoint use to get the information of one single alarm
    """

    def __init__(self):
        super().__init__()
        self.data_model = AlarmsModel
        self.unique = ["id"]

    @doc(
        description="Get an alarm",
        tags=["None"],
    )
    @authenticate(auth_class=Auth())
    @marshal_with(AlarmsResponse(many=True))
    @BaseMetaResource.get_data_or_404
    def get(self, alarm_id):
        """
        API method to get all the data of a specific alarm.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.
        :return: The data of the alarm, and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """

        current_app.logger.info(
            f"User {self.get_user()} gets details of alarm {alarm_id}"
        )

        return self.get_detail(idx=alarm_id)

    @doc(description="Disable an alarm", tags=["None"])
    @authenticate(auth_class=Auth())
    def delete(self, alarm_id):
        """
        :param int alarm_id: Alarm id.
        :return:
        :rtype: Tuple(dict, integer)
        """
                
        current_app.logger.info(
            f"Alarm {alarm_id} was disabled by user {self.get_user()}"
        )
        return self.disable_detail(idx=alarm_id)




