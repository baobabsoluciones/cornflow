"""
Pytest hooks for the cornflow-server test suites.

With pytest-xdist (``pytest -n auto``) every worker is a separate process, so each one
gets its own SQLite file: sharing one file would make the workers drop each other's tables.
The suites still run with ``python -m unittest`` as before; this file is only read by pytest.
"""

import os

_worker = os.environ.get("PYTEST_XDIST_WORKER")
_url = os.environ.get("DATABASE_URL", "sqlite:///cornflow_test.db")

if _worker and _url.startswith("sqlite:///"):
    _base, _ext = os.path.splitext(_url)
    os.environ["DATABASE_URL"] = f"{_base}_{_worker}{_ext or '.db'}"
