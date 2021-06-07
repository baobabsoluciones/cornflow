from flask_testing import LiveServerTestCase
import cornflow_client as cf

from cornflow.app import create_app
from cornflow.commands import AccessInitialization
from cornflow.shared.utils import db
from cornflow.tests.const import PREFIX


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

    def get_server_url(self):
        """
        Return the url of the test server
        """
        prefix = PREFIX
        if prefix:
            prefix += "/"
        return "http://localhost:%s" % self._port_value.value + prefix
