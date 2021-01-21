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
        data = {
            'name': 'testname',
            'email': 'test@test.com',
            'password': 'testpassword'
        }
        user = UserModel(data=data)
        user.save()
        db.session.commit()

        self.token = self.client.post('/login/', data=json.dumps(data), follow_redirects=True,
                                      headers={"Content-Type": "application/json"}).json['token']

        self.user = Auth.return_user_from_token(self.token)
        self.url = None
        self.model = None
        self.id = None
        self.foreign_keys = None

    @staticmethod
    def airflow_user():
        data = {
            'name': 'airflow',
            'email': 'airflow@baobabsoluciones.es',
            'password': 'THISNEEDSTOBECHANGED'
        }

        user = UserModel(data=data)
        user.super_admin = True
        user.save()
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_new_row(self, file):
        with open(file) as f:
            payload = json.load(f)

        if self.foreign_keys is not None:
            for key, value in self.foreign_keys.items():
                payload[key] = value

        response = self.client.post(self.url, data=json.dumps(payload), follow_redirects=True,
                                    headers={"Content-Type": "application/json",
                                             "Authorization": 'Bearer ' + self.token})

        self.assertEqual(201, response.status_code)

        row = self.model.query.get(response.json['id'])
        self.assertEqual(row.id, response.json['id'])
        for key in payload:
            self.assertEqual(getattr(row, key), payload[key])
        return row.id

    def get_rows(self, files):
        data = []
        codes = []

        for file in files:
            with open(file) as f:
                temp = json.load(f)

                if self.foreign_keys is not None:
                    for key, value in self.foreign_keys.items():
                        temp[key] = value

                data.append(temp)
                codes.append(self.create_new_row(file))

        rows = self.client.get(self.url, follow_redirects=True,
                               headers={"Content-Type": "application/json", "Authorization": 'Bearer ' + self.token})

        self.assertEqual(len(rows.json), len(files))

        for i in range(len(data)):
            self.assertEqual(rows.json[i]['id'], codes[i])
            for key in data[i]:
                self.assertEqual(rows.json[i][key], data[i][key])

    def get_one_row(self, file):
        with open(file) as f:
            payload = json.load(f)

        row = self.client.get(self.url, follow_redirects=True,
                              headers={"Content-Type": "application/json", "Authorization": 'Bearer ' + self.token})

        self.assertEqual(200, row.status_code)
        self.assertEqual(row.json['id'], self.id)
        for key in payload:
            self.assertEqual(row.json[key], payload[key])

    def get_no_rows(self):
        rows = self.client.get(self.url, follow_redirects=True,
                               headers={"Content-Type": "application/json", "Authorization": 'Bearer ' + self.token})

        self.assertEqual(204, rows.status_code)

    def update_row(self, file, key, new_value):
        with open(file) as f:
            payload = json.load(f)

        payload[key] = new_value

        response = self.client.put(self.url, data=json.dumps(payload), follow_redirects=True,
                                   headers={"Content-Type": "application/json",
                                            "Authorization": 'Bearer ' + self.token})

        self.assertEqual(200, response.status_code)

        row = self.client.get(self.url, follow_redirects=True,
                              headers={"Content-Type": "application/json", "Authorization": 'Bearer ' + self.token})

        self.assertEqual(200, row.status_code)
        self.assertEqual(row.json['id'], self.id)
        for key in payload:
            self.assertEqual(row.json[key], payload[key])

    def delete_row(self):

        response = self.client.delete(self.url, follow_redirects=True,
                                      headers={"Content-Type": "application/json",
                                               "Authorization": 'Bearer ' + self.token})
        self.assertEqual(200, response.status_code)

        response = self.client.get(self.url, follow_redirects=True,
                                   headers={"Content-Type": "application/json",
                                            "Authorization": 'Bearer ' + self.token})

        self.assertEqual(204, response.status_code)

    def repr_method(self, representation):
        row = self.model.query.get(self.id)
        self.assertEqual(repr(row), representation)

    def str_method(self, string: str):
        row = self.model.query.get(self.id)
        self.assertEqual(str(row), string)
