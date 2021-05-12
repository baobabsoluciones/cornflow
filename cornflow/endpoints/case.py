"""
External endpoints to manage the instances: create new ones, or get all the instances created by the user,
or get only one.
These endpoints have different access url, but manage the same data entities
"""
# Import from libraries
from flask import request, current_app
from werkzeug.utils import secure_filename
from marshmallow.exceptions import ValidationError
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, use_kwargs, doc
import os
import pulp

# Import from internal modules
from .meta_resource import MetaResource
from ..models import InstanceModel
from ..schemas.model_json import DataSchema
from ..schemas.instance import (
    InstanceSchema,
    InstanceEndpointResponse,
    InstanceDetailsEndpointResponse,
    InstanceDataEndpointResponse,
    InstanceRequest,
    InstanceEditRequest,
    InstanceFileRequest,
    QueryFiltersInstance,
)
from ..shared.authentication import Auth
from ..shared.exceptions import InvalidUsage
from cornflow_client.airflow.api import get_schema, validate_and_continue
from ..shared.compress import compressed
from flask_inflate import inflate

#


class CaseEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to create a new instance or get all the instances and their related information
    """

    def __init__(self):
        super().__init__()
        self.model = InstanceModel
        self.query = InstanceModel.get_all_objects
        self.primary_key = "id"

    @doc(description="Get all cases", tags=["Cases"])
    @Auth.auth_required
    # @marshal_with(InstanceEndpointResponse(many=True))
    # @use_kwargs(QueryFiltersInstance, location='json')
    def get(self, **kwargs):
        """
        API (GET) method to get all directory structure of cases for the user
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: a dictionary with a tree structure of the cases and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        return None

    @doc(description="Create an instance", tags=["Instances"])
    @Auth.auth_required
    @inflate
    # @marshal_with(InstanceDetailsEndpointResponse)
    @use_kwargs(InstanceRequest, location="json")
    def post(self, **kwargs):
        """
        API (POST) method to a new case
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: a dictionary with a message(either an error encountered during creation
          or the reference_id of the instance created if successful) and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        data_schema = kwargs.get("data_schema", "pulp")

        if data_schema is None:
            # no schema provided, no validation to do
            return self.post_list(kwargs)

        if data_schema == "pulp":
            # this one we have the schema stored inside cornflow
            validate_and_continue(DataSchema(), kwargs["data"])
            return self.post_list(kwargs)

        # for the rest of the schemas: we need to ask airflow for the schema
        config = current_app.config
        marshmallow_obj = get_schema(config, data_schema)
        validate_and_continue(marshmallow_obj(), kwargs["data"])

        # if we're here, we validated and the data seems to fit the schema
        return self.post_list(kwargs)


class InstanceDetailsEndpointBase(MetaResource, MethodResource):
    """
    Endpoint used to get the information ofa single instance, edit it or delete it
    """

    def __init__(self):
        super().__init__()
        self.model = InstanceModel
        self.primary_key = "id"
        self.query = InstanceModel.get_one_object_from_user
        self.dependents = "executions"

    @doc(description="Get one instance", tags=["Instances"], inherit=False)
    @Auth.auth_required
    @marshal_with(InstanceDetailsEndpointResponse)
    @MetaResource.get_data_or_404
    def get(self, idx):
        """
        API method to get an instance created by the user and its related info.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str idx: ID of the instance
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the instance) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return InstanceModel.get_one_object_from_user(self.get_user(), idx)
