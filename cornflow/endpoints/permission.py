"""

"""

# Import from libraries
from flask_apispec import marshal_with, doc
from flask_apispec.views import MethodResource

# Import from internal modules
from .meta_resource import MetaResource
from ..models import PermissionViewRoleModel
from ..schemas.permission import PermissionViewRoleResponse
from ..shared.authentication import Auth
from ..shared.compress import compressed
from ..shared.const import ADMIN_ROLE
from ..shared.exceptions import EndpointNotImplemented


class PermissionsViewRoleEndpoint(MetaResource, MethodResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.model = PermissionViewRoleModel
        self.query = PermissionViewRoleModel.get_all_objects
        self.primary_key = "id"

    @doc(
        description="Get all the permissions assigned to the roles",
        tags=["PermissionViewRole"],
    )
    @Auth.auth_required
    @marshal_with(PermissionViewRoleResponse(many=True))
    @compressed
    def get(self):
        """

        :return:
        :rtype:
        """
        return PermissionViewRoleModel.get_all_objects()

    @staticmethod
    def post(self):
        return EndpointNotImplemented()


class PermissionsViewRoleDetailEndpoint(MetaResource, MethodResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.model = PermissionViewRoleModel
        self.query = PermissionViewRoleModel.get_all_objects
        self.primary_key = "id"

    def put(self):
        raise EndpointNotImplemented()

    def delete(self):
        raise EndpointNotImplemented()
