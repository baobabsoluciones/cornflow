"""
External endpoints to manage the reports: create new ones, list all of them, get one in particular
These endpoints have different access url, but manage the same data entities
"""
import os

from flask import current_app, request, send_from_directory
from flask_apispec import marshal_with, use_kwargs, doc
from werkzeug.utils import secure_filename
import uuid

from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import ExecutionModel, ReportModel
from cornflow.schemas.reports import (
    ReportSchema,
    ReportEditRequest,
    QueryFiltersReports,
    ReportRequest,
)
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import SERVICE_ROLE
from cornflow.shared.exceptions import (
    FileError,
    ObjectDoesNotExist,
    NoPermission,
)


class ReportEndpoint(BaseMetaResource):
    """
    Endpoint used to create a new report or get all the reports and their information back
    """

    ROLES_WITH_ACCESS = [SERVICE_ROLE]

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

    @doc(description="Create a report", tags=["Reports"])
    @authenticate(auth_class=Auth())
    @use_kwargs(ReportRequest, location="form")
    @marshal_with(ReportSchema)
    def post(self, **kwargs):
        """
        API method to create a new report linked to an existing execution
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed, error if data is not validated or
          the reference_id for the newly created report if successful) and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """

        execution = ExecutionModel.get_one_object(idx=kwargs["execution_id"])

        if execution is None:
            raise ObjectDoesNotExist("The execution does not exist")
        if "file" not in request.files:
            # we're creating an empty report.
            # which is possible
            report = ReportModel(get_report_info(kwargs, execution, None))

            report.save()
            return report, 201

        file = request.files["file"]
        report_name = new_file_name(file)

        report = ReportModel(get_report_info(kwargs, execution, report_name))

        report.save()

        # We try to save the file, if an error is raised then we delete the record on the database
        try:
            write_file(file, execution.id, report_name)
            return report, 201

        except Exception as error:
            report.delete()
            current_app.logger.error(error)
            raise FileError(error=str(error))


class ReportDetailsEndpointBase(BaseMetaResource):
    """
    Endpoint used to get the information of a certain report. But not the data!
    """

    def __init__(self):
        super().__init__()
        self.data_model = ReportModel
        self.foreign_data = {"execution_id": ExecutionModel}


class ReportDetailsEditEndpoint(ReportDetailsEndpointBase):

    ROLES_WITH_ACCESS = [SERVICE_ROLE]

    @doc(description="Edit a report", tags=["Reports"], inherit=False)
    @authenticate(auth_class=Auth())
    @use_kwargs(ReportEditRequest, location="form")
    def put(self, idx, **data):
        """
        Edit an existing report

        :param string idx: ID of the report.
        :return: A dictionary with a message (error if authentication failed, or the report does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        # TODO: forbid non-service users from running put
        current_app.logger.info(f"User {self.get_user()} edits report {idx}")

        report = self.get_detail(idx=idx)

        if "file" not in request.files:
            # we're creating an empty report.
            # which is possible
            report.update(data)
            report.save()
            return {"message": "Updated correctly"}, 200

        # there's two cases,
        # (1) the report already has a file
        # (2) the report doesn't yet have a file
        file = request.files["file"]
        report_name = new_file_name(file)
        old_name = report.file_url
        # we update the report with the new content, including the new name
        report.update(dict(**data, file_url=report_name))

        # We try to save the file, if an error is raised then we delete the record on the database
        try:
            write_file(file, report.execution_id, report_name)
            report.save()

        except Exception as error:
            # we do not save the report
            current_app.logger.error(error)
            raise FileError(error=str(error))

        # if it saves correctly, we delete the old file, if exists
        # if unsuccessful, we still return 201 but log the error
        if old_name is not None:
            try:
                os.remove(get_report_path(report))
            except OSError as error:
                current_app.logger.error(error)
        return {"message": "Updated correctly"}, 200


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
        # TODO: are we able to download the name in the database and not as part of the file?
        current_app.logger.info(f"User {self.get_user()} gets details of report {idx}")
        report = self.get_detail(user=self.get_user(), idx=idx)

        if report is None:
            raise ObjectDoesNotExist

        # if there's no file, we do not return it:
        if report.file_url is None:
            return report, 200

        my_dir = get_report_dir(report.execution_id)
        response = send_from_directory(my_dir, report.file_url)
        response.headers["File-Description"] = report.description
        response.headers["File-Name"] = report.file_url
        return response

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

        # get report objet
        report = self.get_detail(user_id=self.get_user_id(), idx=idx)

        if report is None:
            raise ObjectDoesNotExist

        # delete file
        os.remove(get_report_path(report))

        return self.delete_detail(user_id=self.get_user_id(), idx=idx)


def get_report_dir(execution_id):
    return f"{current_app.config['UPLOAD_FOLDER']}/{execution_id}"


def get_report_path(report):
    try:
        return f"{get_report_dir(report['execution_id'])}/{report['file_url']}"
    except:
        return f"{get_report_dir(report.execution_id)}/{report.file_url}"


def new_file_name(file):

    filename = secure_filename(file.filename)
    filename_extension = filename.split(".")[-1]

    if filename_extension not in current_app.config["ALLOWED_EXTENSIONS"]:
        return {
            "message": f"Invalid file extension. "
            f"Valid extensions are: {current_app.config['ALLOWED_EXTENSIONS']}"
        }, 400

    report_name = f"{uuid.uuid4().hex}.{filename_extension}"

    return report_name


def write_file(file, execution_id, file_name):
    my_directory = get_report_dir(execution_id)

    # we create a directory for the execution
    if not os.path.exists(my_directory):
        current_app.logger.info(f"Creating directory {my_directory}")
        os.mkdir(my_directory)

    save_path = os.path.normpath(os.path.join(my_directory, file_name))

    if "static" not in save_path or ".." in save_path:
        raise NoPermission("Invalid file name")
    file.save(save_path)


def get_report_info(data, execution, file_url=None):
    return {
        "name": data["name"],
        "file_url": file_url,
        "execution_id": execution.id,
        "user_id": execution.user_id,
        "description": data.get("description", ""),
        "state": data.get("state"),
        "state_message": data.get("state_message"),
    }
