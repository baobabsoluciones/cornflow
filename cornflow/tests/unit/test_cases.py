import json
import zlib
import hashlib
from cornflow.shared.utils import hash_json_256
from datetime import datetime, timedelta
from cornflow.models import InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase
from cornflow.tests.const import INSTANCE_URL, INSTANCES_LIST, INSTANCE_PATH

from cornflow.models import CaseModel, UserModel

try:
    date_from_str = datetime.fromisoformat
except:

    def date_from_str(_string):
        return datetime.strptime(_string, "%Y-%m-%d %H:%M:%S.%f")


class TestCasesModels(CustomTestCase):
    def setUp(self):
        super().setUp()

        def load_file(_file):
            with open(_file) as f:
                temp = json.load(f)
            return temp

        self.payload = load_file(INSTANCE_PATH)
        self.payloads = [load_file(f) for f in INSTANCES_LIST]
        parents = [None, 1, 1, 3, 3, 3, 1, 7, 7, 9, 7]
        user = UserModel.get_one_user(self.user)
        data = {**self.payload, **dict(user_id=user.id)}
        for parent in parents:
            if parent is not None:
                parent = CaseModel.get_one_object_from_user(user=user, idx=parent)
            node = CaseModel(data=data, parent=parent)
            node.save()

    def test_new_case(self):
        user = UserModel.get_one_user(self.user)
        case = CaseModel.get_one_object_from_user(user=user, idx=6)
        self.assertEqual(case.path, "1/3/")
        case = CaseModel.get_one_object_from_user(user=user, idx=11)
        self.assertEqual(case.path, "1/7/")

    def test_move_case(self):
        user = UserModel.get_one_user(self.user)
        case6 = CaseModel.get_one_object_from_user(user=user, idx=6)
        case11 = CaseModel.get_one_object_from_user(user=user, idx=11)
        case6.move_to(case11)
        self.assertEqual(case6.path, "1/7/11/")

    def test_move_case2(self):
        user = UserModel.get_one_user(self.user)
        case3 = CaseModel.get_one_object_from_user(user=user, idx=3)
        case11 = CaseModel.get_one_object_from_user(user=user, idx=11)
        case9 = CaseModel.get_one_object_from_user(user=user, idx=9)
        case10 = CaseModel.get_one_object_from_user(user=user, idx=10)
        case3.move_to(case11)
        case9.move_to(case3)
        self.assertEqual(case10.path, "1/7/11/3/9/")

    def test_delete_case(self):
        user = UserModel.get_one_user(self.user)
        case7 = CaseModel.get_one_object_from_user(user=user, idx=7)
        case7.delete()
        case11 = CaseModel.get_one_object_from_user(user=user, idx=11)
        self.assertIsNone(case11)

    def test_descendants(self):
        user = UserModel.get_one_user(self.user)
        case7 = CaseModel.get_one_object_from_user(user=user, idx=7)
        self.assertEqual(len(case7.descendants), 4)

    def test_depth(self):
        user = UserModel.get_one_user(self.user)
        case10 = CaseModel.get_one_object_from_user(user=user, idx=10)
        self.assertEqual(case10.depth, 4)
