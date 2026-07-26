import os
import sys
from importlib import import_module
import warnings


def get_app():
    env = os.getenv("FLASK_ENV", "development")
    data_conn = get_db_conn()
    if env == "production":
        warnings.filterwarnings("ignore")
    external = int(os.getenv("EXTERNAL_APP", 0))
    if external == 0:
        from cornflow.app import create_app
    else:
        sys.path.append("./")
        external_app = os.getenv("EXTERNAL_APP_MODULE", "external_app")
        external_module = import_module(external_app)
        create_app = external_module.create_wsgi_app

    if data_conn is None:
        app = create_app(env)
    else:
        app = create_app(env, data_conn)

    return app


def get_db_conn():
    # An explicit DATABASE_URL (the same variable the running server uses via
    # SQLALCHEMY_DATABASE_URI) always takes precedence, so CLI commands run
    # inside the container (e.g. `cornflow users bi_token`) connect to the
    # exact same database as the server. Without this, DEFAULT_POSTGRES=1
    # (forced in the Docker image) made the CLI rebuild the URL from the
    # CORNFLOW_DB_* defaults and fail to connect when the deployment only
    # provided DATABASE_URL.
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    if int(os.getenv("DEFAULT_POSTGRES", 0)) == 0:
        return "sqlite:///cornflow.db"

    cornflow_db_host = os.getenv("CORNFLOW_DB_HOST", "cornflow_db")
    cornflow_db_port = os.getenv("CORNFLOW_DB_PORT", "5432")
    cornflow_db_user = os.getenv("CORNFLOW_DB_USER", "cornflow")
    cornflow_db_password = os.getenv("CORNFLOW_DB_PASSWORD", "cornflow")
    cornflow_db = os.getenv("CORNFLOW_DB", "cornflow")
    return os.getenv(
        "cornflow_db_conn",
        f"postgresql://{cornflow_db_user}:{cornflow_db_password}@{cornflow_db_host}:{cornflow_db_port}/{cornflow_db}",
    )
