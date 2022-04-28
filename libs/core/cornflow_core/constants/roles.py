"""
This file contains the constants related to the roles of the REST API.
"""
VIEWER_ROLE = 1
PLANNER_ROLE = 2
ADMIN_ROLE = 3
SERVICE_ROLE = 4

ALL_DEFAULT_ROLES = [VIEWER_ROLE, PLANNER_ROLE, ADMIN_ROLE, SERVICE_ROLE]

ROLES_MAP = {
    PLANNER_ROLE: "planner",
    VIEWER_ROLE: "viewer",
    ADMIN_ROLE: "admin",
    SERVICE_ROLE: "service",
}
