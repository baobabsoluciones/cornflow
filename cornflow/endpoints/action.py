"""

"""
# Import from libraries
from flask_apispec import marshal_with, doc
from flask_apispec.views import MethodResource

# Import from internal modules
from .meta_resource import MetaResource
from ..models import ActionModel
from ..schemas.action import ActionsResponse
from ..shared.authentication import Auth
from ..shared.const import ADMIN_ROLE, SUPER_ADMIN_ROLE


class ActionListEndpoint(MetaResource, MethodResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE, SUPER_ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.model = ActionModel
        self.query = ActionModel.get_all_objects
        self.primary_key = "id"

    @doc(description="Get all the actions", tags=["Actions"])
    @Auth.auth_required
    @marshal_with(ActionsResponse(many=True))
    def get(self):
        """

        :return:
        :rtype:
        """
        return ActionModel.get_all_objects()
