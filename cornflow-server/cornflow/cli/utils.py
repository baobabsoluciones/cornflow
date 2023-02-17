import os
import sys
from importlib import import_module


def get_app():
    env = os.getenv("FLASK_ENV", "development")
    external = int(os.getenv("EXTERNAL_APP", 0))
    if external == 0:
        from cornflow import create_app
    else:
        sys.path.append("./")
        external_app = os.getenv("EXTERNAL_APP_MODULE", "external_app")
        external_module = import_module(external_app)
        create_app = external_module.create_wsgi_app

    app = create_app(env)
    return app
