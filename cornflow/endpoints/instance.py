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
from ..schemas.instance import InstanceSchema, \
    InstanceEndpointResponse, InstanceDetailsEndpointResponse, InstanceDataEndpointResponse, \
    InstanceRequest, InstanceEditRequest, InstanceFileRequest
from ..shared.authentication import Auth
from ..shared.exceptions import InvalidUsage
from ..shared.airflow_api import get_schema, validate_and_continue
from ..shared.compress import compressed
from flask_inflate import inflate

# Initialize the schema that all endpoints are going to use
ALLOWED_EXTENSIONS = {'mps', 'lp'}



class InstanceEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to create a new instance or get all the instances and their related information
    """

    def __init__(self):
        super().__init__()
        self.model = InstanceModel
        self.query = 'get_all_instances'
        self.primary_key = 'id'

    @doc(description='Get all instances', tags=['Instances'])
    @Auth.auth_required
    @marshal_with(InstanceEndpointResponse(many=True))
    def get(self):
        """
        API (GET) method to get all the instances created by the user and its related info
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: a dictionary with a message or an object (message if it an error is encountered,
          object with the data from the instances otherwise) and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        if self.is_admin():
            return InstanceModel.get_all_instances_admin()
        return self.get_list(self.get_user_id())

    @doc(description='Create an instance', tags=['Instances'])
    @Auth.auth_required
    @inflate
    @marshal_with(InstanceDetailsEndpointResponse)
    @use_kwargs(InstanceRequest, location='json')
    def post(self, **kwargs):
        """
        API (POST) method to create a new instance
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: a dictionary with a message(either an error encountered during creation
          or the reference_id of the instance created if successful) and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        data_schema = kwargs.get('data_schema', 'pulp')

        if data_schema is None:
            # no schema provided, no validation to do
            return self.post_list(kwargs)

        if data_schema == 'pulp':
            # this one we have the schema stored inside cornflow
            kwargs['data'] = validate_and_continue(DataSchema(), kwargs['data'])
            return self.post_list(kwargs)

        # for the rest of the schemas: we need to ask airflow for the schema
        config = current_app.config
        marshmallow_obj = get_schema(config, data_schema)
        kwargs['data'] = validate_and_continue(marshmallow_obj(), kwargs['data'])

        # if we're here, we validated and the data seems to fit the schema
        return self.post_list(kwargs)


class InstanceDetailsEndpointBase(MetaResource, MethodResource):
    """
    Endpoint used to get the information ofa single instance, edit it or delete it
    """

    def __init__(self):
        super().__init__()
        self.model = InstanceModel
        self.primary_key = 'id'
        self.query = 'get_one_instance_from_user'
        self.dependents = 'executions'

    @doc(description='Get one instance', tags=['Instances'], inherit=False)
    @Auth.auth_required
    @marshal_with(InstanceDetailsEndpointResponse)
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
        if self.is_admin():
            return InstanceModel.get_one_instance_from_id_admin(idx)
        return self.get_detail(self.get_user_id(), idx)


class InstanceDetailsEndpoint(InstanceDetailsEndpointBase):

    @doc(description='Edit an instance', tags=['Instances'])
    @Auth.auth_required
    @use_kwargs(InstanceEditRequest, location='json')
    def put(self, idx, **data):
        """
        API method to edit an existing instance.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str idx: ID of the instance
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return self.put_detail(data, self.get_user_id(), idx)

    @doc(description='Delete an instance', tags=['Instances'])
    @Auth.auth_required
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
        return self.delete_detail(self.get_user_id(), idx)


class InstanceDataEndpoint(InstanceDetailsEndpointBase):
    """
    Endpoint used to get the information ofa single instance, edit it or delete it
    """

    def __init__(self):
        super().__init__()
        self.dependents = None

    @doc(description='Get input data of an instance', tags=['Instances'], inherit=False)
    @Auth.auth_required
    @marshal_with(InstanceDataEndpointResponse)
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
        return self.get_detail(self.get_user_id(), idx)


@doc(description='Create an instance from an mps file', tags=['Instances'], inherit=False)
class InstanceFileEndpoint(MetaResource, MethodResource):
    """
    Endpoint to accept mps files to upload
    """

    @Auth.auth_required
    @marshal_with(InstanceDetailsEndpointResponse)
    @use_kwargs(InstanceFileRequest, location='form', inherit=False)
    def post(self, name, description, minimize=1):
        """

        :param file:
        :return:
        :rtype: Tuple(dict, integer)
        """
        if 'file' not in request.files:
            raise InvalidUsage(error="No file was provided")
        file = request.files['file']
        filename = secure_filename(file.filename)
        if not (file and allowed_file(filename)):
            raise InvalidUsage(error="Could not open file to upload. Check the extension matches {}".
                               format(ALLOWED_EXTENSIONS))
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
            data=problem.toDict()
            ,name=name
            ,description=description
            ,user_id=self.get_user_id()
        )

        try:
            data = InstanceSchema().load(pb_data)
        except ValidationError as val_err:
            raise InvalidUsage(error=val_err.normalized_messages())

        item = InstanceModel(data)
        item.save()

        return item, 201


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
