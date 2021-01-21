import json
from flask_testing import LiveServerTestCase

from cornflow.app import create_app
from cornflow.models import UserModel
from cornflow.shared.utils import db
from cornflow.shared.authentication import Auth

import cornflow_client as cf

class CustomTestCaseLive(LiveServerTestCase):

    def create_app(self):
        app = create_app('testing')
        return app

    def setUp(self):
        server = self.get_server_url()
        db.create_all()
        data = dict(name='testname',
                    email='test@test.com',
                    password='testpassword'
                    )
        user = UserModel(data=data)
        user.save()
        db.session.commit()
        # user = UserModel.query.get(user.id)
        self.client = cf.CornFlow(url=server)
        response = self.client.login(data['email'], data['password'])
        self.user = Auth.return_user_from_token(response['token'])
        self.url = None
        self.model = None

    def tearDown(self):
        db.session.remove()
        db.drop_all()