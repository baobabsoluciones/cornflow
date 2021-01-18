import json

from flask_testing import TestCase
from cornflow.app import create_app
from cornflow.models import UserModel
from cornflow.shared.utils import db


class TestUserEndpoint(TestCase):

    def create_app(self):
        app = create_app('testing')
        return app

    def setUp(self):
        db.create_all()
        self.data = {
            'name': 'testname',
            'email': 'test@test.com',
            'password': 'testpassword'
        }
        user = UserModel(data=self.data)
        user.save()
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_get_all_users(self):
        pass

    def test_get_one_user(self):
        pass
