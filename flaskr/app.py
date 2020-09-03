from flask import Flask
from flask_restful import Api
from .endpoints.instance import InstanceEndpoint
from .endpoints.user import UserEndpoint
from .endpoints.login import LoginEndpoint
from .endpoints.execution import ExecutionEndpoint
from .endpoints.execution_data import ExecutionDataEndpoint
from .endpoints.singup import SingUpEndpoint
from .config import app_config
from .models import db, bcrypt


def create_app(env_name):
    """

    :param env_name:
    :return:
    """

    app = Flask(__name__)
    app.config.from_object(app_config['development'])

    bcrypt.init_app(app)
    db.init_app(app)
    api = Api(app)
    api.add_resource(InstanceEndpoint, '/instance/')
    api.add_resource(ExecutionEndpoint, '/execution/')
    api.add_resource(ExecutionDataEndpoint, '/execution_data/<string:id>/')
    api.add_resource(UserEndpoint, '/user/')
    api.add_resource(LoginEndpoint, '/login/')
    api.add_resource(SingUpEndpoint, '/singup/')

    return app

if __name__ == '__main__':
    # env_name = os.getenv('FLASK_ENV')
    env_name = 'development'
    app = create_app(env_name)
    app.run()