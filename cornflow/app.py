import os

from flask import Flask
from flask_apispec.extension import FlaskApiSpec
from flask_cors import CORS
from flask_restful import Api


from .config import app_config
from .endpoints import resources
from .shared.compress import init_compress
from .shared.exceptions import _initialize_errorhandlers
from .shared.utils import db, bcrypt


def create_app(env_name="development", dataconn=None):
    """

    :param str env_name: 'testing' or 'development' or 'production'
    :return: the application that is going to be running :class:`Flask`
    :rtype: :class:`Flask`
    """

    app = Flask(__name__)
    app.config.from_object(app_config[env_name])
    # initialization for init_cornflow_service.py
    if dataconn is not None:
        app.config["SQLALCHEMY_DATABASE_URI"] = dataconn
    CORS(app)
    bcrypt.init_app(app)
    db.init_app(app)

    if "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"]:

        def _fk_pragma_on_connect(dbapi_con, con_record):
            dbapi_con.execute("pragma foreign_keys=ON")

        with app.app_context():
            from sqlalchemy import event

            event.listen(db.engine, "connect", _fk_pragma_on_connect)

    api = Api(app)
    for res in resources:
        api.add_resource(res["resource"], res["urls"], endpoint=res["endpoint"])

    docs = FlaskApiSpec(app)
    for res in resources:
        docs.register(target=res["resource"], endpoint=res["endpoint"])

    _initialize_errorhandlers(app)
    init_compress(app)
    return app


if __name__ == "__main__":
    environment_name = os.getenv("FLASK_ENV", "development")
    # env_name = 'development'
    app = create_app(environment_name)
    app.run()
