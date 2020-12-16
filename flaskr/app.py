import os

from flask import Flask
from flask_restful import Api

from .config import app_config
from .endpoints.dag import DAGEndpoint
from .endpoints.execution import ExecutionEndpoint, ExecutionDetailsEndpoint, ExecutionStatusEndpoint
from .endpoints.instance import InstanceEndpoint
from .endpoints.login import LoginEndpoint
from .endpoints.signup import SingUpEndpoint
from .endpoints.user import UserEndpoint
from .models import db, bcrypt


def create_app(env_name='development'):
    """

    :param env_name:
    :return:
    """

    app = Flask(__name__)
    app.config.from_object(app_config[env_name])

    bcrypt.init_app(app)
    db.init_app(app)
    api = Api(app)
    api.add_resource(InstanceEndpoint, '/instance/', endpoint="instance")
    api.add_resource(InstanceEndpoint, '/instance/<string:reference_id>/', endpoint="instances")
    api.add_resource(ExecutionEndpoint, '/execution/', endpoint="execution")
    api.add_resource(ExecutionDetailsEndpoint, '/execution/<string:reference_id>/', endpoint="execution-detail")
    api.add_resource(ExecutionStatusEndpoint, '/execution/status/<string:reference_id>/', endpoint="execution-status")
    api.add_resource(DAGEndpoint, '/dag/<string:reference_id>/', endpoint="dag")
    api.add_resource(UserEndpoint, '/user/', endpoint="user")
    api.add_resource(LoginEndpoint, '/login/', endpoint="login")
    api.add_resource(SingUpEndpoint, '/signup/', endpoint="signup")

    return app

if __name__ == '__main__':
    environment_name = os.getenv('FLASK_ENV', 'development')
    # env_name = 'development'
    app = create_app(environment_name)
    app.run()