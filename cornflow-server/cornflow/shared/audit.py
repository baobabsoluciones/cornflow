"""
Structured security audit logging.

Emits one JSON object per security-relevant event on a dedicated logger
("cornflow.audit", configured in log_config with a raw message formatter and
its own stdout handler). This is the emission layer only: collection,
append-only retention, time synchronisation and alerting are the
responsibility of the deployment's log pipeline / SIEM.

Each record has a UTC timestamp, an "audit" marker (for easy filtering), the
event name and outcome, plus the actor, target and source IP when known.
Fields that are not provided are auto-filled from the request context.
"""

import json
import logging
from datetime import datetime, timezone

from flask import current_app, g, has_request_context, request

audit_logger = logging.getLogger("cornflow.audit")


def _client_ip():
    """Source IP of the current request, honouring the trusted-proxy config."""
    if not has_request_context():
        return None
    try:
        trust = int(current_app.config.get("RATELIMIT_TRUST_FORWARDED_FOR", 0))
    except (RuntimeError, TypeError, ValueError):
        trust = 0
    if trust:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.remote_addr


def _current_actor():
    """The authenticated user of the current request, if any."""
    if not has_request_context():
        return None, None
    user = getattr(g, "user", None)
    if user is None:
        return None, None
    return getattr(user, "id", None), getattr(user, "username", None)


def _audit_enabled():
    try:
        return int(current_app.config.get("AUDIT_LOG_ENABLED", 1)) == 1
    except RuntimeError:
        # No application context (e.g. some CLI usages): emit anyway
        return True


def audit(
    event: str,
    outcome: str = "success",
    actor_id=None,
    actor: str = None,
    target_id=None,
    target: str = None,
    **extra,
):
    """
    Emit a structured security audit event as a single JSON line.

    :param str event: the event name (e.g. "login.success", "account.locked")
    :param str outcome: "success" or "failure" (or a more specific value)
    :param actor_id: id of the user performing the action (auto from g.user)
    :param str actor: username performing the action (auto from g.user)
    :param target_id: id of the affected user/resource, if different
    :param str target: name of the affected user/resource, if different
    :param extra: additional event-specific fields (None values are dropped)
    """
    if not _audit_enabled():
        return
    if actor_id is None and actor is None:
        actor_id, actor = _current_actor()

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "audit": True,
        "event": event,
        "outcome": outcome,
    }
    if actor_id is not None:
        record["actor_id"] = actor_id
    if actor is not None:
        record["actor"] = actor
    if target_id is not None:
        record["target_id"] = target_id
    if target is not None:
        record["target"] = target
    ip = _client_ip()
    if ip is not None:
        record["ip"] = ip
    record.update({k: v for k, v in extra.items() if v is not None})

    try:
        audit_logger.info(json.dumps(record, default=str, ensure_ascii=False))
    except Exception:
        # Auditing must never break the request it is recording
        pass
