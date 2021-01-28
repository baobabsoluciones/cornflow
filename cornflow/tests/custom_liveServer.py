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
        user_data =\
            dict(name='testname',
                 email='test@test.com',
                 password='testpassword',
                 super_admin=0
                 )
        admin_data = \
            dict(name='testadmin',
                 email='airflow_test@admin.com',
                 password='airflow_test_password',
                 super_admin=1
                 )
        for data in [user_data, admin_data]:
            user = UserModel(data=data)
            if data.get('super_admin', 0):
                user.super_admin = 1
            user.save()
        db.session.commit()
        self.client = cf.CornFlow(url=server)
        response = self.client.login(user_data['email'], user_data['password'])
        self.user = Auth.return_user_from_token(response['token'])
        self.url = None
        self.model = None

    def tearDown(self):
        db.session.remove()
        db.drop_all()