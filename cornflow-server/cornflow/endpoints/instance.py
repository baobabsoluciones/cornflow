"""
External endpoints to manage the instances: create new ones, or get all the instances created by the user,
or get only one.
These endpoints have different access url, but manage the same data entities
"""

# Import from libraries
from cornflow_client.airflow.api import get_schema
from cornflow_core.resources import BaseMetaResource
from cornflow_core.shared import validate_and_continue
from flask import request, current_app
from flask_apispec import marshal_with, use_kwargs, doc
from flask_inflate import inflate
from marshmallow.exceptions import ValidationError
import os
import pulp
from werkzeug.utils import secure_filename
import logging as log
from cornflow_core.authentication import authenticate

# Import from internal modules
from ..models import InstanceModel
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

from ..schemas.model_json import DataSchema
from ..shared.authentication import Auth
from cornflow_core.compress import compressed
from cornflow_core.exceptions import InvalidUsage


# Initialize the schema that all endpoints are going to use
ALLOWED_EXTENSIONS = {"mps", "lp"}


class InstanceEndpoint(BaseMetaResource):
    """
    Endpoint used to create a new instance or get all the instances and their related information
    """

    def __init__(self):
        super().__init__()
        self.data_model = InstanceModel

    @doc(description="Get all instances", tags=["Instances"])
    @authenticate(auth_class=Auth())
    @marshal_with(InstanceEndpointResponse(many=True))
    @use_kwargs(QueryFiltersInstance, location="query")
    def get(self, **kwargs):
        """
        API (GET) method to get all the instances created by the user and its related info
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: a list of objects with the data and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        log.info(f"User {self.get_user()} gets all the instances")
        return self.get_list(user=self.get_user(), **kwargs)

    @doc(description="Create an instance", tags=["Instances"])
    @authenticate(auth_class=Auth())
    @Auth.dag_permission_required
    @inflate
    @marshal_with(InstanceDetailsEndpointResponse)
    @use_kwargs(InstanceRequest, location="json")
    def post(self, **kwargs):
        """
        API (POST) method to create a new instance
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: an object with the data for the created instance and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        data_schema = kwargs.get("schema", "solve_model_dag")

        if data_schema is None:
            # no schema provided, no validation to do
            return self.post_list(data=kwargs)

        if data_schema == "pulp" or data_schema == "solve_model_dag":
            # this one we have the schema stored inside cornflow
            validate_and_continue(DataSchema(), kwargs["data"])
            return self.post_list(data=kwargs)

        # for the rest of the schemas: we need to ask airflow for the schema
        config = current_app.config
        marshmallow_obj = get_schema(config, data_schema)
        validate_and_continue(marshmallow_obj(), kwargs["data"])

        # if we're here, we validated and the data seems to fit the schema
        response = self.post_list(data=kwargs)
        log.info(f"User {self.get_user()} creates instance {response[0].id}")
        return response


class InstanceDetailsEndpointBase(BaseMetaResource):
    """
    Endpoint used to get the information of a single instance, edit it or delete it
    """

    def __init__(self):
        super().__init__()
        self.data_model = InstanceModel
        self.dependents = "executions"

    @doc(description="Get one instance", tags=["Instances"], inherit=False)
    @authenticate(auth_class=Auth())
    @marshal_with(InstanceDetailsEndpointResponse)
    @BaseMetaResource.get_data_or_404
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
        log.info(f"User {self.get_user()} gets instance {idx}")
        return self.get_detail(user=self.get_user(), idx=idx)


class InstanceDetailsEndpoint(InstanceDetailsEndpointBase):
    @doc(description="Edit an instance", tags=["Instances"])
    @authenticate(auth_class=Auth())
    @Auth.dag_permission_required
    @use_kwargs(InstanceEditRequest, location="json")
    def put(self, idx, **kwargs):
        """
        API method to edit an existing instance.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str idx: ID of the instance
        :return: A dictionary with a confirmation message and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        schema = InstanceModel.get_one_object(user=self.get_user(), idx=idx).schema

        if kwargs.get("data") is not None and schema is not None:
            if schema == "pulp" or schema == "solve_model_dag":
                # this one we have the schema stored inside cornflow
                validate_and_continue(DataSchema(), kwargs["data"])
            else:
                # for the rest of the schemas: we need to ask airflow for the schema
                config = current_app.config
                marshmallow_obj = get_schema(config, schema)
                validate_and_continue(marshmallow_obj(), kwargs["data"])

        response = self.put_detail(data=kwargs, user=self.get_user(), idx=idx)
        log.info(f"User {self.get_user()} edits instance {idx}")
        return response

    @doc(description="Delete an instance", tags=["Instances"])
    @authenticate(auth_class=Auth())
    def delete(self, idx):
        """
        API method to delete an existing instance.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str idx: ID of the instance
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        response = self.delete_detail(user=self.get_user(), idx=idx)
        log.info(f"User {self.get_user()} deletes instance {idx}")
        return response


class InstanceDataEndpoint(InstanceDetailsEndpointBase):
    """
    Endpoint used to get the information o fa single instance, edit it or delete it
    """

    def __init__(self):
        super().__init__()
        self.dependents = None

    @doc(description="Get input data of an instance", tags=["Instances"], inherit=False)
    @authenticate(auth_class=Auth())
    @marshal_with(InstanceDataEndpointResponse)
    @BaseMetaResource.get_data_or_404
    @compressed
    def get(self, idx):
        """
        API method to get an instance data by the user and its related info.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str idx: ID of the instance
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the instance) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        response = self.get_detail(user=self.get_user(), idx=idx)
        log.info(f"User {self.get_user()} gets the data of case {idx}")
        return response


class InstanceFileEndpoint(BaseMetaResource):
    """
    Endpoint to accept mps files to upload
    """

    @doc(
        description="Create an instance from an mps file",
        tags=["Instances"],
        inherit=False,
    )
    @authenticate(auth_class=Auth())
    @marshal_with(InstanceDetailsEndpointResponse)
    @use_kwargs(InstanceFileRequest, location="form", inherit=False)
    def post(self, name, description, minimize=1):
        """

        :param str name:
        :param str description:
        :param int minimize:
        :return: a tuple with the created instance and a integer with the status code
        :rtype: Tuple(:class:`InstanceModel`, 201)
        """
        if "file" not in request.files:
            raise InvalidUsage(error="No file was provided")
        file = request.files["file"]
        filename = secure_filename(file.filename)
        if not (file and allowed_file(filename)):
            raise InvalidUsage(
                error=f"Could not open file to upload. Check the extension matches {ALLOWED_EXTENSIONS}"
            )
        file.save(filename)
        sense = 1 if minimize else -1
        try:
            _vars, problem = pulp.LpProblem.fromMPS(filename, sense=sense)
        except:
            raise InvalidUsage(error="There was an error reading the file")
        try:
            os.remove(filename)
        except:
            pass

        pb_data = dict(
            data=problem.toDict(),
            name=name,
            description=description,
            user_id=self.get_user_id(),
        )

        try:
            data = InstanceSchema().load(pb_data)
        except ValidationError as val_err:
            raise InvalidUsage(error=val_err.normalized_messages())

        item = InstanceModel(data)
        item.schema = "solve_model_dag"
        item.save()
        log.info(f"User {self.get_user()} creates instance {item.id} from mps file")
        return item, 201


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
