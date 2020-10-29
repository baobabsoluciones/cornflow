from flask import Flask
from flask_restful import Api

from .config import app_config
from .endpoints import InstanceEndpoint, InstanceDetailsEndpoint, UserEndpoint, LoginEndpoint, ExecutionEndpoint, ExecutionDetailsEndpoint, \
    ExecutionStatusEndpoint, DAGEndpoint, SingUpEndpoint
from .shared.utils import db, bcrypt


def create_app(environment):
    """

    :param str environment:
    :return: the application that is going to be running :class:`Flask`
    :rtype: :class:`Flask`
    """

    app = Flask(__name__)
    app.config.from_object(app_config['development'])

    bcrypt.init_app(app)
    db.init_app(app)
    api = Api(app)
    api.add_resource(InstanceEndpoint, '/instance/', endpoint="instance")
    api.add_resource(InstanceDetailsEndpoint, '/instance/<string:reference_id>', endpoint="instance-detail")
    api.add_resource(ExecutionEndpoint, '/execution/', endpoint="execution")
    api.add_resource(ExecutionDetailsEndpoint, '/execution/<string:reference_id>/', endpoint="execution-detail")
    api.add_resource(ExecutionStatusEndpoint, '/execution/status/<string:reference_id>/', endpoint="execution-status")
    api.add_resource(DAGEndpoint, '/dag/<string:reference_id>/', endpoint="dag")
    api.add_resource(UserEndpoint, '/user/', endpoint="user")
    api.add_resource(LoginEndpoint, '/login/', endpoint="login")
    api.add_resource(SingUpEndpoint, '/signup/', endpoint="signup")

    return app


if __name__ == '__main__':
    # env_name = os.getenv('FLASK_ENV')
    env_name = 'development'
    app = create_app(env_name)
    app.run()
