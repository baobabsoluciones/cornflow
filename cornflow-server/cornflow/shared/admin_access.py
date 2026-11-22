"""
Administration rights that depend on the security level and the reserved role
range. The permission table decides who reaches each endpoint; these helpers
cover what the table can not express.
"""
from flask import current_app, has_app_context

from cornflow.shared.const import (
    CLIENT_ADMIN_REVOKE_ADMIN_MAX_LEVEL,
    LEVEL_PERMISSION_ASSIGNATION,
    RESERVED_ROLE_RANGE,
    STRICTEST_SECURITY_LEVEL,
)
from cornflow.shared.security_levels import SECURITY_LEVELS


def current_security_level() -> int:
    """
    Effective security level of the running application (app.config
    SECURITY_LEVEL). Without application context, or without a valid level in
    the configuration, the strictest level.
    """
    if not has_app_context():
        return STRICTEST_SECURITY_LEVEL
    try:
        level = int(current_app.config.get("SECURITY_LEVEL"))
    except (TypeError, ValueError):
        return STRICTEST_SECURITY_LEVEL
    if level not in SECURITY_LEVELS:
        return STRICTEST_SECURITY_LEVEL
    return level


def level_permission_assignation(level: int = None) -> list:
    """
    (role_id, action_id, endpoint) permissions that the given security level
    (by default the current one) adds to the base permissions. A copy: the
    caller can extend it.
    """
    if level is None:
        level = current_security_level()
    return list(LEVEL_PERMISSION_ASSIGNATION.get(level, []))


def client_admin_can_revoke_admin(level: int = None) -> bool:
    """
    Whether a client admin (not a platform administrator) can revoke the admin
    role from a user at the given level (by default the current one).
    """
    if level is None:
        level = current_security_level()
    return level <= CLIENT_ADMIN_REVOKE_ADMIN_MAX_LEVEL


def is_reserved_role_id(role_id) -> bool:
    """
    Whether a role id falls inside RESERVED_ROLE_RANGE (900-999), where the
    cornflow platform roles live. None and non integers give False.
    """
    try:
        role_id = int(role_id)
    except (TypeError, ValueError):
        return False
    low, high = RESERVED_ROLE_RANGE
    return low <= role_id <= high
