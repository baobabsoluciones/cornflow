"""
External endpoints to manage the instances: create new ones, or get all the instances created by the user,
or get only one.
These endpoints have different access url, but manage the smae data entities
"""
# Import from libraries
from flask import request

# Import from internal modules
from .meta_resource import MetaResource
from ..models import InstanceModel
from ..schemas import InstanceSchema
from ..shared import Auth

# Initialize the schema that all endpoints are going to use
instance_schema = InstanceSchema()


class InstanceEndpoint(MetaResource):
    """
    Endpoint used to create a new instance or get all the instances and their related information
    """
    def __init__(self):
        super().__init__()
        self.model = InstanceModel
        self.query = 'get_all_instances'
        self.schema = InstanceSchema()
        self.external_primary_key = 'reference_id'
        self.output_name = 'instance_id'

    def get(self):
        """
        API (GET) method to get all the instances created by the user and its related info
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: a dictionary with a message or an object (message if it an error is encountered,
        object with the data from the instances otherwise) and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        # TODO: if super_admin or admin should it be able to get any instance?
        # TODO: return 204 if no instances have been created by the user
        return self.get_list(request)

    @Auth.auth_required
    def post(self):
        """
        API (POST) method to create a new instance
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: a dictionary with a message(either an error encountered during creation
        or the reference_id of the instance created if successful) and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        return self.post_list(request)


class InstanceDetailsEndpoint(MetaResource):
    def __init__(self):
        super().__init__()
        self.model = InstanceModel
        # TODO: should this query use user as well?
        self.query = 'get_one_instance_from_reference'
        self.schema = InstanceSchema()

    def get(self, reference_id):
        return self.get_detail(request, reference_id)

    def put(self, reference_id):
        return self.put_detail(request, reference_id)

    @Auth.auth_required
    def delete(self, reference_id):
        user_id, admin, super_admin = Auth.return_user_info(request)
        instance = InstanceModel.get_one_instance_from_user(user_id, reference_id)

        # TODO: for now they get disabled instead of getting permanently deleted
        for execution in instance.executions:
            execution.disable()
        if instance:
            instance.disable()
        return {}, 204
