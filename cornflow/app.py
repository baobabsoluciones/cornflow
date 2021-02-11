import os

from flask import Flask
from flask_cors import CORS
from flask_restful import Api
from flask_apispec.extension import FlaskApiSpec
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

from .config import app_config
from .endpoints import resources
from .shared.exceptions import _initialize_errorhandlers
from .shared.utils import db, bcrypt


def create_app(env_name='development'):
    """

    :param str environment:
    :return: the application that is going to be running :class:`Flask`
    :rtype: :class:`Flask`
    """

    app = Flask(__name__)
    app.config.from_object(app_config[env_name])
    if env_name == 'development' or env_name == 'testing':
        # TODO: not sure if we should keep this line and if so, here.
        CORS(app)
    bcrypt.init_app(app)
    db.init_app(app)

    api = Api(app)
    for res in resources:
        api.add_resource(res['resource'], res['urls'], endpoint=res['endpoint'])

    # apispec time
    app.config.update({
        'APISPEC_SPEC': APISpec(
            title='Cornflow API docs',
            version='v1',
            plugins=[MarshmallowPlugin()],
            openapi_version='2.0.0'
        ),
        'APISPEC_SWAGGER_URL': '/swagger/',  # URI to access API Doc JSON
        'APISPEC_SWAGGER_UI_URL': '/swagger-ui/'  # URI to access UI of API Doc
    })
    docs = FlaskApiSpec(app)
    for res in resources:
        docs.register(target=res['resource'], endpoint=res['endpoint'])

    _initialize_errorhandlers(app)
    return app


if __name__ == '__main__':
    environment_name = os.getenv('FLASK_ENV', 'development')
    # env_name = 'development'
    app = create_app(environment_name)
    app.run()
