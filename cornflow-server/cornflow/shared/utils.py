"""

"""
import hashlib
import json
from cornflow_backend.shared import database
from cornflow_backend.shared import password_crypt

# from flask_sqlalchemy import SQLAlchemy
# from flask_bcrypt import Bcrypt

db = database
bcrypt = password_crypt


def hash_json_256(data):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
