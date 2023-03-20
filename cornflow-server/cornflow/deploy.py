from gevent import monkey

monkey.patch_all()

from cornflow.app import app


def create_app(env_name="development", dataconn: str = None):
    return app(env_name, dataconn)
