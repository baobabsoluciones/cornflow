# Imports from libraries
from flask import current_app
from flask_apispec import doc, marshal_with, use_kwargs

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import AlarmsModel
from cornflow.schemas.alarms import (
    AlarmEditRequest,
    AlarmsResponse,
    AlarmsPostRequest,
    QueryFiltersAlarms,
)
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.exceptions import AirflowError, ObjectDoesNotExist, InvalidData
from cornflow.shared.const import SERVICE_ROLE


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


class AlarmDetailEndpointBase(BaseMetaResource):
    """
    Endpoint used to get the information of a certain alarm. But not the data!
    """

    def __init__(self):
        super().__init__()
        self.data_model = AlarmsModel
        self.unique = ["id"]


class AlarmDetailEndpoint(AlarmDetailEndpointBase):
    @doc(description="Get details of an alarm", tags=["None"], inherit=False)
    @authenticate(auth_class=Auth())
    @marshal_with(AlarmsResponse)
    @BaseMetaResource.get_data_or_404
    def get(self, idx):
        """
        API method to get an execution created by the user and its related info.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the execution) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        current_app.logger.info(
            f"User {self.get_user()} gets details of execution {idx}"
        )
        return self.get_detail(idx=idx)

    @doc(description="Edit an execution", tags=["Executions"], inherit=False)
    @authenticate(auth_class=Auth())
    @use_kwargs(AlarmEditRequest, location="json")
    def put(self, idx, **data):
        """
        Edit an existing alarm

        :param string idx: ID of the alarm.
        :return: A dictionary with a message (error if authentication failed, or the alarm does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        current_app.logger.info(f"User {self.get_user()} edits alarm {idx}")
        return self.put_detail(data, track_user=False, idx=idx)

    @doc(description="Disable an alarm", tags=["None"])
    @authenticate(auth_class=Auth())
    def delete(self, idx):
        """
        :param int alarm_id: Alarm id.
        :return:
        :rtype: Tuple(dict, integer)
        """

        current_app.logger.info(f"Alarm {idx} was disabled by user {self.get_user()}")
        return self.disable_detail(idx=idx)
