from gevent import monkey

monkey.patch_all()
from .app import create_app as cornflow


def create_app(env_name="development", dataconn=None):
    return cornflow(env_name=env_name)
