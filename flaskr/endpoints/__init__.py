"""
Initialization file for the endpoints module
All references to endpoints should be imported from here
"""

from .dag import DAGEndpoint
from .execution import ExecutionEndpoint, ExecutionDetailsEndpoint, ExecutionStatusEndpoint
from .instance import InstanceEndpoint, InstanceDetailsEndpoint
from .login import LoginEndpoint
from .signup import SignUpEndpoint
from .user import UserEndpoint, UserDetailEndpoint
