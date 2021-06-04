"""
Initialization file for the endpoints module
All references to endpoints should be imported from here
"""

from .action import ActionListEndpoint
from .apiview import ApiViewListEndpoint

from .case import (
    CaseEndpoint,
    CaseFromInstanceExecutionEndpoint,
    CaseCopyEndpoint,
    CaseDetailsEndpoint,
    CaseDataEndpoint,
    CaseToInstance,
    CaseCompare,
)
from .dag import DAGEndpoint, DAGEndpointManual

from .execution import (
    ExecutionEndpoint,
    ExecutionDetailsEndpoint,
    ExecutionStatusEndpoint,
    ExecutionDataEndpoint,
    ExecutionLogEndpoint,
)

from .health import HealthEndpoint

from .instance import (
    InstanceEndpoint,
    InstanceDetailsEndpoint,
    InstanceFileEndpoint,
    InstanceDataEndpoint,
)

from .login import LoginEndpoint
from .permission import PermissionsViewRoleEndpoint
from .roles import RolesListEndpoint, RoleDetailEndpoint
from .schemas import SchemaEndpoint
from .signup import SignUpEndpoint
from .user import UserEndpoint, UserDetailsEndpoint, ToggleUserAdmin


resources = [
    dict(resource=InstanceEndpoint, urls="/instance/", endpoint="instance"),
    dict(
        resource=InstanceDetailsEndpoint,
        urls="/instance/<string:idx>/",
        endpoint="instances-detail",
    ),
    dict(
        resource=InstanceDataEndpoint,
        urls="/instance/<string:idx>/data/",
        endpoint="instances-data",
    ),
    dict(
        resource=InstanceFileEndpoint, urls="/instancefile/", endpoint="instance-file"
    ),
    dict(
        resource=ExecutionDetailsEndpoint,
        urls="/execution/<string:idx>/",
        endpoint="execution-detail",
    ),
    dict(
        resource=ExecutionStatusEndpoint,
        urls="/execution/<string:idx>/status/",
        endpoint="execution-status",
    ),
    dict(
        resource=ExecutionDataEndpoint,
        urls="/execution/<string:idx>/data/",
        endpoint="execution-data",
    ),
    dict(
        resource=ExecutionLogEndpoint,
        urls="/execution/<string:idx>/log/",
        endpoint="execution-log",
    ),
    dict(resource=ExecutionEndpoint, urls="/execution/", endpoint="execution"),
    dict(resource=DAGEndpoint, urls="/dag/<string:idx>/", endpoint="dag"),
    dict(resource=DAGEndpointManual, urls="/dag/", endpoint="dag-manual"),
    dict(resource=UserEndpoint, urls="/user/", endpoint="user"),
    dict(
        resource=UserDetailsEndpoint,
        urls="/user/<int:user_id>/",
        endpoint="user-detail",
    ),
    dict(
        resource=ToggleUserAdmin,
        urls="/user/<int:user_id>/<int:make_admin>/",
        endpoint="user-admin",
    ),
    dict(resource=LoginEndpoint, urls="/login/", endpoint="login"),
    dict(resource=SignUpEndpoint, urls="/signup/", endpoint="signup"),
    dict(resource=SchemaEndpoint, urls="/schema/<string:dag_name>/", endpoint="schema"),
    dict(resource=HealthEndpoint, urls="/health/", endpoint="health"),
    dict(
        resource=CaseFromInstanceExecutionEndpoint,
        urls="/case/instance/",
        endpoint="case-instance-execution",
    ),
    dict(resource=CaseCopyEndpoint, urls="/case/<int:idx>/copy/", endpoint="case-copy"),
    dict(resource=CaseEndpoint, urls="/case/", endpoint="case"),
    dict(resource=CaseDetailsEndpoint, urls="/case/<int:idx>/", endpoint="case-detail"),
    dict(resource=CaseDataEndpoint, urls="/case/<int:idx>/data/", endpoint="case-data"),
    dict(
        resource=CaseToInstance,
        urls="/case/<int:idx>/instance/",
        endpoint="case-instance",
    ),
    dict(
        resource=CaseCompare,
        urls="/case/<int:idx1>/<int:idx2>/",
        endpoint="case-compare",
    ),
    dict(resource=ActionListEndpoint, urls="/action/", endpoint="actions"),
    dict(
        resource=PermissionsViewRoleEndpoint,
        urls="/permission/",
        endpoint="permissions",
    ),
    dict(resource=RolesListEndpoint, urls="/roles/", endpoint="roles"),
    dict(
        resource=RoleDetailEndpoint, urls="/roles/<int:idx>/", endpoint="roles-detail"
    ),
    dict(resource=ApiViewListEndpoint, urls="/apiview/", endpoint="api-view"),
]
