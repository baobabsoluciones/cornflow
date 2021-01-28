import json

from cornflow.tests.custom_test_case import TestCase
from cornflow.app import create_app
from cornflow.models import UserModel
from cornflow.shared.utils import db


class TestUserEndpoint(TestCase):

    def create_app(self):
        app = create_app('testing')
        return app

    def setUp(self):
        db.create_all()
        self.url = '/user/'
        self.model = UserModel
        self.data = dict(name='testname', email='test@test.com', password='testpassword', admin=False)
        self.admin = dict(name='anAdminUser', email='admin@admin.com', password='testpassword', admin=True)
        self.super_admin = dict(name='anAdminSuperUser', email='super_admin@admin.com',
                                password='tpass_super_admin', super_admin=True, admin=False)
        self.login_keys = ['email', 'password']
        self.items_to_check = ['email', 'name', 'id', 'admin']

        for u_data in [self.data, self.admin, self.super_admin]:
            user = UserModel(data=u_data)
            user.admin = u_data.get('admin', False)
            user.super_admin = u_data.get('super_admin', False)
            user.save()
            u_data['id'] = user.id
        db.session.commit()
        # users = UserModel.get_all_users()
        # for user in users:
        #     print(user.name, user.admin)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def get_user(self, user_asks, user_asked=None):
        data = {k: user_asks[k] for k in self.login_keys}
        url = self.url
        if user_asked is not None:
            url += '{}/'.format(user_asked['id'])
        token = self.client.post('/login/', data=json.dumps(data), follow_redirects=True,
                                      headers={"Content-Type": "application/json"}).json['token']
        return self.client.get(url, follow_redirects=True,
                               headers={"Content-Type": "application/json", "Authorization": 'Bearer ' + token})

    def make_admin(self, user_asks, user_asked, make_admin=1):
        data = {k: user_asks[k] for k in self.login_keys}
        url = '{}{}/{}/'.format(self.url, user_asked['id'], make_admin)
        token = self.client.post('/login/', data=json.dumps(data), follow_redirects=True,
                                      headers={"Content-Type": "application/json"}).json['token']
        return self.client.put(url, follow_redirects=True,
                               headers={"Content-Type": "application/json", "Authorization": 'Bearer ' + token})

    def test_get_all_users_superadmin(self):
        # the superadmin should be able to list all users
        response = self.get_user(self.super_admin)
        self.assertEqual(200, response.status_code)
        self.assertEqual(len(response.json), 3)

    def test_get_all_users_user(self):
        # a simple user should not be able to do it
        response = self.get_user(self.data)
        self.assertEqual(400, response.status_code)
        self.assertTrue('error' in response.json)

    def test_get_all_users_admin(self):
        # an admin should not be able to do it
        response = self.get_user(self.admin)
        self.assertEqual(400, response.status_code)
        self.assertTrue('error' in response.json)

    def test_get_same_user(self):
        # if a user asks for itself: it's ok
        for u_data in [self.data, self.admin, self.super_admin]:
            response = self.get_user(u_data, u_data)
            self.assertEqual(200, response.status_code)
            for item in self.items_to_check:
                # print(u_data['name'], item)
                self.assertEqual(response.json[item], u_data[item])

    def test_get_another_user(self):
        response = self.get_user(self.data, self.admin)
        self.assertEqual(400, response.status_code)
        self.assertTrue('error' in response.json)

    def test_get_another_user_admin(self):
        response = self.get_user(self.admin, self.data)
        self.assertEqual(200, response.status_code)
        for item in self.items_to_check:
            self.assertEqual(response.json[item], self.data[item])

    def test_user_makes_someone_admin(self):
        response = self.make_admin(self.data, self.data)
        self.assertEqual(400, response.status_code)

    def test_admin_makes_someone_admin(self):
        response = self.make_admin(self.admin, self.data)
        self.assertEqual(400, response.status_code)

    def zz_test_super_admin_makes_someone_admin(self):
        response = self.make_admin(self.super_admin, self.data)
        self.assertEqual(201, response.status_code)
        for item in self.items_to_check:
            if item == 'admin':
                self.assertTrue(response.json[item])
            else:
                self.assertEqual(response.json[item], self.data[item])

    def zz_test_super_admin_takes_someone_admin(self):
        response = self.make_admin(self.super_admin, self.admin, 0)
        self.assertEqual(201, response.status_code)
        for item in self.items_to_check:
            if item == 'admin':
                self.assertFalse(response.json[item])
            else:
                self.assertEqual(response.json[item], self.admin[item])