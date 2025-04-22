"""
Shared constants for the application
"""

# Default role IDs
VIEWER_ROLE_ID = 1
PLANNER_ROLE_ID = 2
ADMIN_ROLE_ID = 3
SERVICE_ROLE_ID = 4

# Default roles with descriptions
DEFAULT_ROLES = [
    {
        "id": ADMIN_ROLE_ID,
        "name": "admin",
        "description": "Administrator role with full access to all system features and data",
    },
    {
        "id": SERVICE_ROLE_ID,
        "name": "service",
        "description": "Service account role for automated processes, monitoring and system operations",
    },
    {
        "id": PLANNER_ROLE_ID,
        "name": "planner",
        "description": "Planner role with access to basic system features",
    },
    {
        "id": VIEWER_ROLE_ID,
        "name": "viewer",
        "description": "Read-only role with limited access to view data",
    },
]

# Default action IDs
READ_ACTION_ID = 1
CREATE_ACTION_ID = 2
UPDATE_ACTION_ID = 3
DELETE_ACTION_ID = 4

# Default actions with descriptions
DEFAULT_ACTIONS = [
    {
        "id": READ_ACTION_ID,
        "name": "read",
        "description": "Permission to retrieve and view data from the system",
    },
    {
        "id": CREATE_ACTION_ID,
        "name": "create",
        "description": "Permission to create new data in the system",
    },
    {
        "id": UPDATE_ACTION_ID,
        "name": "update",
        "description": "Permission to modify existing data in the system",
    },
    {
        "id": DELETE_ACTION_ID,
        "name": "delete",
        "description": "Permission to remove data from the system",
    },
]

# HTTP method to CRUD action mapping
HTTP_METHOD_TO_ACTION = {
    "GET": READ_ACTION_ID,
    "POST": CREATE_ACTION_ID,
    "PUT": UPDATE_ACTION_ID,
    "PATCH": UPDATE_ACTION_ID,
    "DELETE": DELETE_ACTION_ID,
}

# Default permission assignments
# Format: (role_id, action_id)
DEFAULT_PERMISSIONS = [
    # Viewer permissions - read-only
    (VIEWER_ROLE_ID, READ_ACTION_ID),
    # Planner permissions - full CRUD
    (PLANNER_ROLE_ID, READ_ACTION_ID),
    (PLANNER_ROLE_ID, CREATE_ACTION_ID),
    (PLANNER_ROLE_ID, UPDATE_ACTION_ID),
    (PLANNER_ROLE_ID, DELETE_ACTION_ID),
    # Admin permissions - full access
    (ADMIN_ROLE_ID, READ_ACTION_ID),
    (ADMIN_ROLE_ID, CREATE_ACTION_ID),
    (ADMIN_ROLE_ID, UPDATE_ACTION_ID),
    (ADMIN_ROLE_ID, DELETE_ACTION_ID),
    # Service permissions - full access
    (SERVICE_ROLE_ID, READ_ACTION_ID),
    (SERVICE_ROLE_ID, CREATE_ACTION_ID),
    (SERVICE_ROLE_ID, UPDATE_ACTION_ID),
    (SERVICE_ROLE_ID, DELETE_ACTION_ID),
]

DEFAULT_PERMISSIONS_BLACKLIST = [
    (VIEWER_ROLE_ID, READ_ACTION_ID, "/users"),
    (PLANNER_ROLE_ID, READ_ACTION_ID, "/users"),
    (VIEWER_ROLE_ID, READ_ACTION_ID, "/roles"),
    (PLANNER_ROLE_ID, READ_ACTION_ID, "/roles"),
    (PLANNER_ROLE_ID, CREATE_ACTION_ID, "/roles"),
    (PLANNER_ROLE_ID, UPDATE_ACTION_ID, "/roles/<role_id>"),
    (PLANNER_ROLE_ID, DELETE_ACTION_ID, "/roles/<role_id>"),
]


PATH_BLACKLIST = [
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/login",
    "/signup",
]
