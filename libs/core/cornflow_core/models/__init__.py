# Import generic first
from .meta_models import EmptyBaseModel
from .meta_models import TraceAttributesModel

# Import particular after
from .action import ActionBaseModel
from .role import RoleBaseModel
from .user import UserBaseModel
from .user_role import UserRoleBaseModel
from .view import ViewBaseModel