"""

"""
# Import from libraries
from flask_apispec import doc, marshal_with, use_kwargs
from flask_apispec.views import MethodResource

# Import from internal modules
from .meta_resource import MetaResource
from ..models import RoleModel
from ..schemas.roles import RolesRequest, RolesResponse
from ..shared.authentication import Auth
from ..shared.const import ADMIN_ROLE, SUPER_ADMIN_ROLE


class RolesListEndpoint(MetaResource, MethodResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE, SUPER_ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.model = RoleModel
        self.query = RoleModel.get_all_objects
        self.primary_key = "id"

    @doc()
    @Auth.auth_required
    @marshal_with(RolesResponse(many=True))
    def get(self):
        return RoleModel.get_all_objects()

    @doc()
    @Auth.auth_required
    @use_kwargs(RolesRequest, location="json")
    @marshal_with(RolesResponse)
    def post(self, **kwargs):
        return self.post_list(kwargs)


class RoleDetailEndpoint(MetaResource, MethodResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE, SUPER_ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.model = RoleModel
        self.query = RoleModel.get_all_objects
        self.primary_key = "id"

    def put(self):
        pass

    def delete(self):
        pass
