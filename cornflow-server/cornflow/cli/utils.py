import os
import sys
from importlib import import_module
import warnings


def get_app():
    env = os.getenv("FLASK_ENV", "development")
    data_conn = os.getenv("DATABASE_URL", "sqlite:///cornflow.db")
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
