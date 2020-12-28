import json
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.models import UserModel
from cornflow.shared.utils import db


class CustomTestCase(TestCase):

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

        self.token = self.client.post('/login/', data=json.dumps(self.data), follow_redirects=True,
                                      headers={"Content-Type": "application/json"}).json['token']

        self.url = None
        self.model = None
        self.payload = None

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_new_row(self):
        response = self.client.post(self.url, data=json.dumps(self.payload), follow_redirects=True,
                                    headers={"Content-Type": "application/json",
                                             "Authorization": 'Bearer ' + self.token})

        self.assertEqual(201, response.status_code)

        row = self.model.query.get(response.json['id'])
        self.assertEqual(row.id, response.json['id'])
        for key in self.payload:
            self.assertEqual(getattr(row, key), self.payload[key])

    def get_rows(self):
        pass

    def get_one_row(self):
        pass

    def update_row(self):
        pass

    def delete_row(self):
        pass