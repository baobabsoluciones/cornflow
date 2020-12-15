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
from ..shared.authentication import Auth

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
        self.primary_key = 'id'

    @Auth.auth_required
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
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        return self.get_list(self.user_id)

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
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        return self.post_list(request)


class InstanceDetailsEndpoint(MetaResource):
    def __init__(self):
        super().__init__()
        self.model = InstanceModel
        # TODO: should this query use user as well?
        self.query = 'get_one_instance_from_user'
        self.schema = InstanceSchema()
        self.dependents = 'executions'

    @Auth.auth_required
    def get(self, idx):
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        return self.get_detail(self.user_id, idx)

    @Auth.auth_required
    def put(self, idx):
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        return self.put_detail(request, self.user_id, idx)

    @Auth.auth_required
    def delete(self, idx):
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        return self.delete_detail(self.user_id, idx)
