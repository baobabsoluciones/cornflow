"""
Initialization file for the endpoints module
All references to endpoints should be imported from here
The login resource gets created on app startup as it depends on configuration
"""

from .action import ActionListEndpoint
from .alarms import AlarmsEndpoint, AlarmDetailEndpoint
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
from .dag import (
    DAGDetailEndpoint,
    DAGEndpointManual,
    DAGCaseEndpoint,
    DAGInstanceEndpoint,
    DeployedDAGEndpoint,
    DeployedDagDetailEndpoint,
)
from .data_check import (
    DataCheckExecutionEndpoint,
    DataCheckInstanceEndpoint,
    DataCheckCaseEndpoint,
)
from .example_data import ExampleDataListEndpoint, ExampleDataDetailEndpoint
from .execution import (
    ExecutionEndpoint,
    ExecutionDetailsEndpoint,
    ExecutionStatusEndpoint,
    ExecutionDataEndpoint,
    ExecutionLogEndpoint,
    ExecutionRelaunchEndpoint,
)
from .health import HealthEndpoint
from .instance import (
    InstanceEndpoint,
    InstanceDetailsEndpoint,
    InstanceFileEndpoint,
    InstanceDataEndpoint,
)
from .licenses import LicensesEndpoint
from .main_alarms import MainAlarmsEndpoint
from .permission import PermissionsViewRoleEndpoint, PermissionsViewRoleDetailEndpoint
from .roles import RolesListEndpoint, RoleDetailEndpoint
from .schemas import SchemaDetailsEndpoint, SchemaEndpoint
from .tables import TablesEndpoint, TablesDetailsEndpoint
from .token import TokenEndpoint
from .user import UserEndpoint, UserDetailsEndpoint, ToggleUserAdmin, RecoverPassword
from .user_role import UserRoleListEndpoint, UserRoleDetailEndpoint

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
        resource=DataCheckExecutionEndpoint,
        urls="/data-check/execution/<string:idx>/",
        endpoint="data-check-execution",
    ),
    dict(
        resource=DataCheckInstanceEndpoint,
        urls="/data-check/instance/<string:idx>/",
        endpoint="data-check-instance",
    ),
    dict(
        resource=DataCheckCaseEndpoint,
        urls="/data-check/case/<int:idx>/",
        endpoint="data-check-case",
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
    dict(
        resource=ExecutionRelaunchEndpoint,
        urls="/execution/<string:idx>/relaunch/",
        endpoint="execution-relaunch",
    ),
    dict(resource=ExecutionEndpoint, urls="/execution/", endpoint="execution"),
    dict(resource=DAGDetailEndpoint, urls="/dag/<string:idx>/", endpoint="dag"),
    dict(resource=DAGEndpointManual, urls="/dag/", endpoint="dag-manual"),
    dict(
        resource=DAGInstanceEndpoint,
        urls="/dag/instance/<string:idx>/",
        endpoint="dag-instance",
    ),
    dict(
        resource=DAGCaseEndpoint,
        urls="/dag/case/<int:idx>/",
        endpoint="dag-case",
    ),
    dict(resource=DeployedDAGEndpoint, urls="/dag/deployed/", endpoint="deployed-dag"),
    dict(
        resource=DeployedDagDetailEndpoint,
        urls="/dag/deployed/<string:idx>/",
        endpoint="deployed-dag-detail",
    ),
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
    dict(resource=TokenEndpoint, urls="/token/", endpoint="token"),
    dict(resource=SchemaEndpoint, urls="/schema/", endpoint="schema"),
    dict(
        resource=SchemaDetailsEndpoint,
        urls="/schema/<string:dag_name>/",
        endpoint="schema-details",
    ),
    dict(
        resource=ExampleDataListEndpoint,
        urls="/example/<string:dag_name>/",
        endpoint="example-data",
    ),
    dict(
        resource=ExampleDataDetailEndpoint,
        urls="/example/<string:dag_name>/<string:example_name>/",
        endpoint="example-data-detail",
    ),
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
    dict(
        resource=PermissionsViewRoleDetailEndpoint,
        urls="/permission/<int:idx>/",
        endpoint="permission-detail",
    ),
    dict(resource=RolesListEndpoint, urls="/roles/", endpoint="roles"),
    dict(
        resource=RoleDetailEndpoint, urls="/roles/<int:idx>/", endpoint="roles-detail"
    ),
    dict(resource=ApiViewListEndpoint, urls="/apiview/", endpoint="api-view"),
    dict(resource=UserRoleListEndpoint, urls="/user/role/", endpoint="user-roles"),
    dict(
        resource=UserRoleDetailEndpoint,
        urls="/user/role/<int:user_id>/<int:role_id>/",
        endpoint="user-roles-detail",
    ),
    dict(
        resource=RecoverPassword,
        urls="/user/recover-password/",
        endpoint="recover-password",
    ),
    dict(
        resource=LicensesEndpoint,
        urls="/licences/",
        endpoint="licences",
    ),
    dict(
        resource=TablesEndpoint, urls="/table/<string:table_name>/", endpoint="tables"
    ),
    dict(
        resource=TablesDetailsEndpoint,
        urls="/table/<string:table_name>/<string:idx>/",
        endpoint="tables-detail",
    ),
]


alarms_resources = [
    dict(
        resource=AlarmsEndpoint,
        urls="/alarms/",
        endpoint="alarms",
    ),
    dict(
        resource=AlarmDetailEndpoint,
        urls="/alarms/<int:idx>/",
        endpoint="alarms-detail",
    ),
    dict(
        resource=MainAlarmsEndpoint,
        urls="/main-alarms/",
        endpoint="main-alarms",
    ),
]
