from flask_testing import LiveServerTestCase
import cornflow_client as cf

from cornflow.app import create_app
from cornflow.shared.utils import db


class CustomTestCaseLive(LiveServerTestCase):

    def create_app(self):
        app = create_app('testing')
        return app

    def set_client(self, server):
        self.client = cf.CornFlow(url=server)
        return self.client

    def setUp(self, create_all=True):
        if create_all:
            db.create_all()
        user_data =\
            dict(name='testname',
                 email='test@test.com',
                 pwd='testpassword',
                 )
        self.set_client(self.get_server_url())
        try:
            response = self.client.login(user_data['email'], user_data['pwd'])
        except cf.CornFlowApiError:
            response = self.client.sign_up(**user_data).json()
        self.client.token = response['token']
        self.url = None
        self.model = None
        self.items_to_check = []

    def tearDown(self):
        # this can be a remote test server, do no touch!
        pass