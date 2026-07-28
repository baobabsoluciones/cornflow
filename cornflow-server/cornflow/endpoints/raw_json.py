"""
Helper for building HTTP responses that splice already-serialized JSON
text directly into the response body, skipping the decode-into-Python /
re-encode-to-JSON round trip for columns that are returned verbatim.

Only safe for fields that are never transformed before being returned:
the DB is trusted to hold valid JSON in the column, and that text is
passed straight through to the client unchanged.
"""

import json

from flask import Response, current_app

from cornflow.shared.const import USER_ACCESS_ALL_OBJECTS_NO


def restrict_to_owner(query, model, user):
    """
    Mirrors the ownership filter in `BaseDataModel.get_one_object`: a
    non-admin, non-service user only sees their own rows, unless the
    deployment has `USER_ACCESS_ALL_OBJECTS` enabled. Endpoints querying
    the ORM entity directly get this for free; endpoints building their
    own Core-style query (to skip JSON decode on huge columns) need to
    apply it explicitly, since they bypass `get_one_object` entirely.

    :param query: a SQLAlchemy query/session.query(...) object
    :param model: the model class being queried (must have `user_id`)
    :param user: the requesting `UserModel` (must be authenticated -- callers
      pass `self.get_user()`, which never returns `None`: it raises
      `InvalidUsage` instead)
    :return: the query, filtered by owner if required
    """
    user_access = int(current_app.config["USER_ACCESS_ALL_OBJECTS"])
    if (
        not user.is_admin()
        and not user.is_service_user()
        and user_access == USER_ACCESS_ALL_OBJECTS_NO
    ):
        query = query.filter(model.user_id == user.id)
    return query


def raw_json_object_response(fields, status=200):
    """
    Build a `flask.Response` whose body is a single JSON object.

    :param fields: ordered list of (key, value, is_raw) tuples.
      When `is_raw` is True, `value` must already be a valid JSON string
      (typically fetched via `sqlalchemy.cast(col, db.Text)` to skip the
      column's normal JSON decode), or None (encoded as the JSON literal
      ``null``). When `is_raw` is False, `value` is encoded normally with
      `json.dumps`.
    :param int status: HTTP status code for the response
    :return: a `flask.Response` with ``Content-Type: application/json``
    :rtype: `flask.Response`
    """
    parts = []
    for key, value, is_raw in fields:
        if is_raw:
            encoded_value = "null" if value is None else value
        else:
            encoded_value = json.dumps(value)
        parts.append(f"{json.dumps(key)}: {encoded_value}")
    body = "{" + ", ".join(parts) + "}"
    return Response(body, mimetype="application/json", status=status)
