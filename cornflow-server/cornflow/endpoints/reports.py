"""
External endpoints to manage the reports: create new ones, list all of them, get one in particular
These endpoints have different access url, but manage the same data entities
"""

# Import from libraries
from flask import current_app
from flask_apispec import marshal_with, use_kwargs, doc

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import ExecutionModel, ReportModel

from cornflow.schemas.reports import (
    ReportSchema,
    ReportEditRequest,
    QueryFiltersReports,
    ReportRequest,
)
from cornflow.shared.authentication import Auth, authenticate


class ReportEndpoint(BaseMetaResource):
    """
    Endpoint used to create a new report or get all the reports and their information back
    """

    def __init__(self):
        super().__init__()
        self.model = ReportModel
        self.data_model = ReportModel
        self.foreign_data = {"execution_id": ExecutionModel}

    @doc(description="Get all reports", tags=["Reports"])
    @authenticate(auth_class=Auth())
    @marshal_with(ReportSchema(many=True))
    @use_kwargs(QueryFiltersReports, location="query")
    def get(self, **kwargs):
        """
        API method to get all the reports created by the user and its related info
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed or a list with all the reports
          created by the authenticated user) and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        reports = self.get_list(user=self.get_user(), **kwargs)
        current_app.logger.info(f"User {self.get_user()} gets list of reports")
        return reports

    @doc(description="Create an report", tags=["Reports"])
    @authenticate(auth_class=Auth())
    @Auth.dag_permission_required
    @marshal_with(ReportSchema)
    @use_kwargs(ReportRequest, location="json")
    def post(self, **kwargs):
        """
        API method to create a new report linked to an already existing report
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed, error if data is not validated or
          the reference_id for the newly created report if successful) and a integer wit the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        # TODO: not sure if it should be possible to generate a report from the REST API
        #  and if so, should we let them upload a new report file?

        response = self.post_list(data=kwargs)
        current_app.logger.info(
            f"User {self.get_user()} creates report {response[0].id}"
        )
        return response


class ReportDetailsEndpointBase(BaseMetaResource):
    """
    Endpoint used to get the information of a certain report. But not the data!
    """

    def __init__(self):
        super().__init__()
        self.data_model = ReportModel
        self.foreign_data = {"execution_id": ExecutionModel}


class ReportDetailsEndpoint(ReportDetailsEndpointBase):
    @doc(description="Get details of a report", tags=["Reports"], inherit=False)
    @authenticate(auth_class=Auth())
    @marshal_with(ReportSchema)
    @BaseMetaResource.get_data_or_404
    def get(self, idx):
        """
        API method to get a report created by the user and its related info.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str idx: ID of the report.
        :return: A dictionary with a message (error if authentication failed, or the report does not exist or
          the data of the report) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        current_app.logger.info(f"User {self.get_user()} gets details of report {idx}")
        return self.get_detail(user=self.get_user(), idx=idx)

    @doc(description="Edit a report", tags=["Reports"], inherit=False)
    @authenticate(auth_class=Auth())
    @use_kwargs(ReportEditRequest, location="json")
    def put(self, idx, **data):
        """
        Edit an existing report

        :param string idx: ID of the report.
        :return: A dictionary with a message (error if authentication failed, or the report does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        current_app.logger.info(f"User {self.get_user()} edits report {idx}")
        return self.put_detail(data, user=self.get_user(), idx=idx)

    @doc(description="Delete a report", tags=["Reports"], inherit=False)
    @authenticate(auth_class=Auth())
    def delete(self, idx):
        """
        API method to delete a report created by the user and its related info.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param string idx: ID of the report.
        :return: A dictionary with a message (error if authentication failed, or the report does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        current_app.logger.info(f"User {self.get_user()} deleted report {idx}")
        return self.delete_detail(user=self.get_user(), idx=idx)
