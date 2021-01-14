import json
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.models import UserModel
from cornflow.shared.utils import db
from cornflow.shared.authentication import Auth


class CustomTestCase(TestCase):

    def create_app(self):
        app = create_app('testing')
        return app

    def setUp(self):
        db.create_all()
        # TODO: no need to store data in self. It's not used but in this function
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

        self.user = Auth.return_user_from_token(self.token)
        self.url = None
        self.model = None
        # TODO: this is not needed since it's filled and tested inside each function
        self.payload = None

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_new_row(self, file):
        with open(file) as f:
            self.payload = json.load(f)

            response = self.client.post(self.url, data=json.dumps(self.payload), follow_redirects=True,
                                        headers={"Content-Type": "application/json",
                                                 "Authorization": 'Bearer ' + self.token})

            self.assertEqual(201, response.status_code)

        row = self.model.query.get(response.json['id'])
        self.assertEqual(row.id, response.json['id'])
        for key in self.payload:
            self.assertEqual(getattr(row, key), self.payload[key])

    def get_rows(self, files):
        self.payload = []
        codes = []
        for file in files:
            with open(file) as f:
                self.payload.append(json.load(f))

            response = self.client.post(self.url, data=json.dumps(self.payload[-1]), follow_redirects=True,
                                        headers={"Content-Type": "application/json",
                                                 "Authorization": 'Bearer ' + self.token})
            codes.append(response.json['id'])

            self.assertEqual(201, response.status_code)

        rows = self.client.get(self.url, follow_redirects=True,
                               headers={"Content-Type": "application/json", "Authorization": 'Bearer ' + self.token})

        for i in range(len(self.payload)):
            self.assertEqual(rows.json[i]['id'], codes[i])
            for key in self.payload[i]:
                self.assertEqual(rows.json[i][key], self.payload[i][key])

    def get_one_row(self):
        pass

    def get_no_rows(self):
        response = self.client.get(self.url, follow_redirects=True,
                                   headers={"Content-Type": "application/json", "Authorization": 'Bearer ' + self.token})

        self.assertEqual(204, response.status_code)

    def update_row(self):
        pass

    def delete_row(self):
        pass