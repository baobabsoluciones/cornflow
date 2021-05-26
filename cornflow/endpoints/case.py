"""
External endpoints to manage the instances: create new ones, or get all the instances created by the user,
or get only one.
These endpoints have different access url, but manage the same data entities
"""

# Import from libraries
from cornflow_client.airflow.api import get_schema, validate_and_continue
from flask import current_app
from flask_apispec import marshal_with, use_kwargs, doc
from flask_apispec.views import MethodResource
from flask_inflate import inflate
from ..shared.compress import compressed

# Import from internal modules
from .meta_resource import MetaResource
from ..models import CaseModel, ExecutionModel, InstanceModel
from ..schemas.case import (
    CaseBase,
    CaseFromInstanceExecution,
    CaseRawRequest,
    CaseSchema,
    CaseListResponse,
)
from ..schemas.instance import (
    QueryFiltersInstance,
)
from ..shared.authentication import Auth
from ..shared.exceptions import InvalidData


#


class CaseEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to create a new case or get all the cases and their related information
    """

    def __init__(self):
        super().__init__()
        self.model = CaseModel
        self.query = CaseModel.get_all_objects
        self.primary_key = "id"

    @doc(description="Get all cases", tags=["Cases"])
    @Auth.auth_required
    @marshal_with(CaseListResponse(many=True))
    @use_kwargs(QueryFiltersInstance, location="query")
    def get(self, **kwargs):
        """
        API (GET) method to get all directory structure of cases for the user
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: a dictionary with a tree structure of the cases and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        return CaseModel.get_all_objects(self.get_user(), **kwargs)

    @doc(description="Create a new case from raw data", tags=["Cases"])
    @Auth.auth_required
    @inflate
    @marshal_with(CaseListResponse)
    @use_kwargs(CaseRawRequest, location="json")
    def post(self, **kwargs):
        """ """
        return self.post_list(kwargs)


class CaseFromInstanceExecutionEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to create a new case from an already existing instance and execution
    """

    def __init__(self):
        super().__init__()
        self.model = CaseModel
        self.query = self.model.get_all_objects
        self.primary_key = "id"
        self.map_instance_fields = {"data": "data", "schema": "schema"}
        self.map_execution_fields = {"solution": "data"}

    @doc(description="Create a new case from instance and execution", tags=["Cases"])
    @Auth.auth_required
    @inflate
    @marshal_with(CaseListResponse)
    @use_kwargs(CaseFromInstanceExecution, location="json")
    def post(self, **kwargs):
        """ """
        instance_id = kwargs.get("instance_id", None)
        execution_id = kwargs.get("execution_id", None)

        data = {
            "name": kwargs.get("name", ""),
            "description": kwargs.get("description", ""),
            "path": kwargs.get("path", ""),
        }

        if instance_id is not None and execution_id is not None:
            raise InvalidData(
                error="Send only instance or execution id", status_code=400
            )

        elif instance_id is not None:
            instance = InstanceModel.get_one_object_from_user(
                self.get_user(), instance_id
            )

            instance_data = {
                key: getattr(instance, value)
                for key, value in self.map_instance_fields.items()
            }

            data = {**data, **instance_data}

        elif execution_id is not None:
            execution = ExecutionModel.get_one_object_from_user(
                self.get_user(), kwargs.get("execution_id", None)
            )

            instance = InstanceModel.get_one_object_from_user(
                self.get_user(), execution.instance_id
            )

            execution_data = {
                key: getattr(execution, value)
                for key, value in self.map_execution_fields.items()
            }

            instance_data = {
                key: getattr(instance, value)
                for key, value in self.map_instance_fields.items()
            }

            data = {**data, **instance_data, **execution_data}

        return self.post_list(data)


class CaseCopyEndpoint(MetaResource, MethodResource):
    """
    Copies the case to a new case. Original case id goes in the url
    """

    def __init__(self):
        super().__init__()
        self.model = CaseModel
        self.query = self.model.get_all_objects
        self.primary_key = "id"
        self.fields_to_copy = [
            "name",
            "description",
            "data",
            "schema",
            "solution",
            "path",
        ]
        self.fields_to_modify = ["name"]

    @doc(description="Copies a case to a new one", tags=["Cases"])
    @Auth.auth_required
    @inflate
    @marshal_with(CaseListResponse)
    @use_kwargs(CaseSchema, location="json")
    def post(self, **kwargs):
        """ """
        case = self.model.get_one_object_from_user(self.get_user(), kwargs.get("id"))
        data = case.__dict__
        payload = dict()
        for key in data.keys():
            if key in self.fields_to_copy:
                payload[key] = data[key]
            if key in self.fields_to_modify:
                payload[key] = "Copy_" + payload[key]
        return self.post_list(payload)


class CaseDetailsEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to get the information ofa single instance, edit it or delete it
    """

    def __init__(self):
        super().__init__()
        self.model = CaseModel
        self.primary_key = "id"
        self.query = CaseModel.get_one_object_from_user

    @doc(description="Get one case", tags=["Cases"], inherit=False)
    @Auth.auth_required
    @marshal_with(CaseListResponse)
    @MetaResource.get_data_or_404
    def get(self, idx):
        """
        API method to get an case created by the user and its related info.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str idx: ID of the case
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the instance) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return CaseModel.get_one_object_from_user(self.get_user(), idx)


class CaseDataEndpoint(CaseDetailsEndpoint):
    @doc(description="Get data of a case", tags=["Cases"], inherit=False)
    @Auth.auth_required
    @marshal_with(CaseBase)
    @MetaResource.get_data_or_404
    @compressed
    def get(self, idx):
        """
        API method to get data for a case by the user and its related info.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str idx: ID of the case
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the instance) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return CaseModel.get_one_object_from_user(self.get_user(), idx)
