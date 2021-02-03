import os

from flask import Flask
from flask_cors import CORS
from flask_restful import Api
from flask_apispec.extension import FlaskApiSpec
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

from .config import app_config
from .endpoints import \
    InstanceEndpoint, InstanceDetailsEndpoint, InstanceDataEndpoint, InstanceFileEndpoint, \
    UserEndpoint, UserDetailsEndpoint, LoginEndpoint, \
    ExecutionEndpoint, ExecutionDetailsEndpoint, ExecutionStatusEndpoint, ExecutionDataEndpoint, ExecutionLogEndpoint, \
    DAGEndpoint, SignUpEndpoint, ToggleUserAdmin
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

    # TODO: maybe move the add_endpoints to a function inside endpoints/__init__.py
    api = Api(app)
    api.add_resource(InstanceEndpoint, '/instance/', endpoint="instance")
    api.add_resource(InstanceDetailsEndpoint, '/instance/<string:idx>/', endpoint="instances-detail")
    api.add_resource(InstanceDataEndpoint, '/instance/<string:idx>/data/', endpoint="instances-data")
    api.add_resource(InstanceFileEndpoint, '/instancefile/', endpoint="instance-file")
    api.add_resource(ExecutionDetailsEndpoint, '/execution/<string:idx>/', endpoint="execution-detail")
    api.add_resource(ExecutionStatusEndpoint, '/execution/<string:idx>/status/', endpoint="execution-status")
    api.add_resource(ExecutionDataEndpoint, '/execution/<string:idx>/data/', endpoint="execution-data")
    api.add_resource(ExecutionLogEndpoint, '/execution/<string:idx>/log/', endpoint="execution-log")
    api.add_resource(ExecutionEndpoint, '/execution/', endpoint="execution")
    api.add_resource(DAGEndpoint, '/dag/<string:idx>/', endpoint="dag")
    api.add_resource(UserEndpoint, '/user/', endpoint="user")
    api.add_resource(UserDetailsEndpoint, '/user/<int:user_id>/', endpoint="user-detail")
    api.add_resource(ToggleUserAdmin, '/user/<int:user_id>/<int:make_admin>/', endpoint="user-admin")
    api.add_resource(LoginEndpoint, '/login/', endpoint="login")
    api.add_resource(SignUpEndpoint, '/signup/', endpoint="signup")

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
    docs.register(InstanceEndpoint, endpoint="instance")
    docs.register(InstanceDetailsEndpoint, endpoint="instances-detail")
    _initialize_errorhandlers(app)



    return app


if __name__ == '__main__':
    environment_name = os.getenv('FLASK_ENV', 'development')
    # env_name = 'development'
    app = create_app(environment_name)
    app.run()
