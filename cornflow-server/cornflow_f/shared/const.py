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
