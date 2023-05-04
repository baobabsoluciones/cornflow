# Full imports
import os

import cornflow_client as cf
from cornflow.shared import db

# External libraries
from flask import current_app
from flask_testing import LiveServerTestCase

# Internal modules
from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.models import UserRoleModel
from cornflow.shared.const import ADMIN_ROLE, SERVICE_ROLE
from cornflow.tests.const import PREFIX


class CustomTestCaseLive(LiveServerTestCase):
    def create_app(self):
        app = create_app("testing")
        app.config["LIVESERVER_PORT"] = 5050
        return app

    def set_client(self, server):
        self.client = cf.CornFlow(url=server)
        return self.client

    def login_or_signup(self, user_data):
        try:
            response = self.client.login(user_data["username"], user_data["pwd"])
        except cf.CornFlowApiError:
            response = self.client.sign_up(**user_data)
        return response

    def setUp(self, create_all=True):
        if create_all:
            db.create_all()
        access_init_command(False)
        register_deployed_dags_command_test(verbose=False)
        user_data = dict(
            username="testname",
            email="test@test.com",
            pwd="Testpassword1!",
        )
        self.set_client(self.get_server_url())
        response = self.login_or_signup(user_data)
        self.client.token = response["token"]
        self.url = None
        self.model = None
        self.items_to_check = []
        register_dag_permissions_command(
            open_deployment=current_app.config["OPEN_DEPLOYMENT"], verbose=False
        )
        os.environ["CORNFLOW_SERVICE_USER"] = "service_user"

        self.create_service_user(
            dict(
                username="service_user", pwd="Airflow_test_password1", email="su@cf.com"
            )
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_user_with_role(self, role_id, data=None):
        if data is None:
            data = {
                "username": "testuser" + str(role_id),
                "email": "testemail" + str(role_id) + "@test.org",
                "password": "Testpassword1!",
            }
        response = self.login_or_signup(data)
        user_role = UserRoleModel({"user_id": response["id"], "role_id": role_id})
        user_role.save()

        db.session.commit()

        return self.login_or_signup(data)["token"]

    def create_service_user(self, data=None):
        return self.create_user_with_role(SERVICE_ROLE, data=data)

    def create_admin(self, data=None):
        return self.create_user_with_role(ADMIN_ROLE, data=data)

    def get_server_url(self):
        """
        Return the url of the test server
        """
        prefix = PREFIX
        if prefix:
            prefix += "/"
        return "http://localhost:%s" % self._port_value.value + prefix
