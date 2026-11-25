"""
This file defines the database session with SQLAlchemy and the password encryption with Bcrypt.
Additionally we add the option to have our database models inherit ABCMeta class so that abstract methods can be defined
"""
from abc import ABCMeta
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.model import Model, DefaultMeta
import hashlib
import json
from sqlalchemy.ext.declarative import declarative_base

from cornflow.shared.const import CORNFLOW_BLUEPRINT_NAME, LEGACY_ENDPOINT_SUFFIX


def logical_endpoint_name(endpoint):
    """
    Returns the logical name of a Flask endpoint of the core.

    The core resources are registered in the ``cornflow`` blueprint
    (``cornflow.login``) and as legacy aliases with the ``_compat`` suffix
    (``login`` + legacy suffix); both resolve to the same logical name (``login``).
    ``None`` and endpoints of other blueprints (plugins) are returned as is.

    :param endpoint: the value of ``request.endpoint``
    :type endpoint: str or None
    :return: the logical endpoint name
    :rtype: str or None
    """
    if not endpoint:
        return endpoint
    prefix = f"{CORNFLOW_BLUEPRINT_NAME}."
    if endpoint.startswith(prefix):
        return endpoint[len(prefix):]
    # Legacy unprefixed routes: delete this block together with them
    if endpoint.endswith(LEGACY_ENDPOINT_SUFFIX):
        return endpoint[: -len(LEGACY_ENDPOINT_SUFFIX)]
    return endpoint


def hash_json_256(data):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class CustomABCMeta(DefaultMeta, ABCMeta):
    """
    Custom meta class so that the models inherit ABCMeta
    """

    pass


db = SQLAlchemy(
    model_class=declarative_base(cls=Model, metaclass=CustomABCMeta, name="Model")
)
bcrypt = Bcrypt()
