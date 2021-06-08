from flask_testing import LiveServerTestCase
import cornflow_client as cf
import json

from cornflow.app import create_app
from cornflow.commands import AccessInitialization
from cornflow.shared.utils import db
from cornflow.tests.const import PREFIX

from cornflow.models import UserModel, UserRoleModel
from cornflow.shared.const import ADMIN_ROLE, SERVICE_ROLE
from cornflow.tests.const import LOGIN_URL, SIGNUP_URL


class CustomTestCaseLive(LiveServerTestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def set_client(self, server):
        self.client = cf.CornFlow(url=server)
        return self.client

    def login_or_signup(self, user_data):
        try:
            response = self.client.login(user_data["email"], user_data["pwd"])
        except cf.CornFlowApiError:
            response = self.client.sign_up(**user_data).json()
        return response

    def setUp(self, create_all=True):
        if create_all:
            db.create_all()
        AccessInitialization().run()
        user_data = dict(
            name="testname",
            email="test@test.com",
            pwd="testpassword",
        )
        self.set_client(self.get_server_url())
        response = self.login_or_signup(user_data)
        self.client.token = response["token"]
        self.url = None
        self.model = None
        self.items_to_check = []

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_user_with_role(self, role_id, data=None):
        if data is None:
            data = {
                "name": "testuser" + str(role_id),
                "email": "testemail" + str(role_id) + "@test.org",
                "password": "testpassword",
            }
        response = self.login_or_signup(data)
        user_role = UserRoleModel({"user_id": response["id"], "role_id": role_id})
        user_role.save()

        db.session.commit()
        data.pop("name")

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
