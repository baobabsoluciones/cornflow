import json
import zlib
import hashlib
from cornflow.shared.utils import hash_json_256
from cornflow.models import InstanceModel, ExecutionModel
from cornflow.tests.custom_test_case import CustomTestCase, BaseTestCases
from cornflow.tests.const import (
    INSTANCE_URL,
    INSTANCES_LIST,
    INSTANCE_PATH,
    EXECUTION_PATH,
    EXECUTION_URL_NORUN,
    CASE_INSTANCE_URL,
    CASE_URL,
    CASE_COPY_URL,
    CASE_PATH,
    CASES_LIST,
)

from cornflow.models import CaseModel, UserModel


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


class TestCasesFromInstanceExecutionEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()

        payload = self.load_file(INSTANCE_PATH)
        instance_id = self.create_new_row(INSTANCE_URL, InstanceModel, payload=payload)

        payload = self.load_file(EXECUTION_PATH, "instance_id", instance_id)
        execution_id = self.create_new_row(
            EXECUTION_URL_NORUN, ExecutionModel, payload=payload
        )

        self.url = CASE_INSTANCE_URL
        self.model = CaseModel
        self.items_to_check = ["name", "description", "path", "schema"]
        self.response_items = [
            "name",
            "description",
            "data",
            "data_hash",
            "schema",
            "solution",
            "solution_hash",
            "user_id",
            "path",
        ]

        self.payload = {
            "name": "testcase",
            "description": "test case for unit tests",
            "instance_id": instance_id,
            "execution_id": execution_id,
            "path": "",
        }
        self.user_object = UserModel.get_one_user(self.user)
        self.instance = InstanceModel.get_one_object_from_user(
            self.user_object, instance_id
        )
        self.execution = ExecutionModel.get_one_object_from_user(
            self.user_object, execution_id
        )

    def test_new_case_execution(self):
        self.payload.pop("instance_id")

        created_case = self.model.get_one_object_from_user(
            self.user_object, self.create_new_row(self.url, self.model, self.payload)
        )

        self.payload["data"] = self.instance.data
        self.payload["data_hash"] = self.instance.data_hash
        self.payload["schema"] = self.instance.schema
        self.payload["solution"] = self.execution.data
        self.payload["solution_hash"] = self.execution.data_hash
        self.payload["user_id"] = self.user

        for key in self.response_items:
            self.assertEqual(self.payload[key], getattr(created_case, key))

    def test_new_case_instance(self):
        self.payload.pop("execution_id")
        created_case = self.model.get_one_object_from_user(
            self.user_object, self.create_new_row(self.url, self.model, self.payload)
        )

        self.payload["data"] = self.instance.data
        self.payload["data_hash"] = self.instance.data_hash
        self.payload["schema"] = self.instance.schema
        self.payload["user_id"] = self.user
        self.payload["solution"] = None
        self.payload["solution_hash"] = hash_json_256(None)
        for key in self.response_items:
            self.assertEqual(self.payload[key], getattr(created_case, key))

    def test_case_not_created(self):
        self.create_new_row(
            self.url, self.model, self.payload, expected_status=400, check_payload=False
        )


class TestCasesRawDataEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.payload = self.load_file(CASE_PATH)
        self.url = CASE_URL
        self.model = CaseModel
        self.items_to_check = ["name", "description", "path", "schema"]

    def test_new_case(self):
        self.create_new_row(self.url, self.model, self.payload)

    def test_new_case_without_solution(self):
        # payload = dict(self.payload)
        # payload.pop("solution")
        self.create_new_row(self.url, self.model, self.payload)


class TestCaseCopyEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        payload = self.load_file(CASE_PATH)
        self.model = CaseModel
        self.items_to_check = ["name", "description", "path", "schema"]
        self.case_id = self.create_new_row(CASE_URL, self.model, payload)
        self.payload = {"id": self.case_id}
        self.url = CASE_COPY_URL
        self.copied_items = [
            "description",
            "data",
            "data_hash",
            "schema",
            "solution",
            "solution_hash",
            "user_id",
            "path",
        ]

        self.modified_items = ["name"]
        self.new_items = ["created_at", "updated_at"]

    def test_copy_case(self):
        new_case_id = self.create_new_row(self.url, self.model, self.payload)
        user = UserModel.get_one_user(self.user)

        original_case = CaseModel.get_one_object_from_user(user, self.case_id)
        new_case = CaseModel.get_one_object_from_user(user, new_case_id)

        for key in self.copied_items:
            self.assertEqual(getattr(original_case, key), getattr(new_case, key))

        for key in self.modified_items:
            self.assertNotEqual(getattr(original_case, key), getattr(new_case, key))
            self.assertEqual(
                "Copy_" + getattr(original_case, key), getattr(new_case, key)
            )

        for key in self.new_items:
            self.assertNotEqual(getattr(original_case, key), getattr(new_case, key))


class TestCaseListEndpoint(BaseTestCases.ListFilters):
    def setUp(self):
        super().setUp()
        self.payload = self.load_file(CASE_PATH)
        self.payloads = [self.load_file(f) for f in CASES_LIST]
        self.model = CaseModel
        self.items_to_check = ["name", "description", "path", "schema"]
        self.url = CASE_URL

    def test_get_rows(self):
        self.get_rows(self.url, self.payloads)


class TestCaseDetailEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.payload = self.load_file(CASE_PATH)
        self.model = CaseModel
        self.items_to_check = [
            "name",
            "description",
            "path",
            "schema",
            "data_hash",
            "solution_hash",
        ]
        self.response_items = {
            "id",
            "name",
            "description",
            "path",
            "schema",
            "data_hash",
            "solution_hash",
            "created_at",
            "updated_at",
        }
        self.url = CASE_URL

    def test_get_one_case(self):
        idx = self.create_new_row(self.url, self.model, self.payload)
        payload = {**self.payload, **dict(id=idx)}
        result = self.get_one_row(self.url + str(idx) + "/", payload)
        diff = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(diff), 0)

    def test_get_nonexistent_instance(self):
        self.get_one_row(
            self.url + "500" + "/", {}, expected_status=404, check_payload=False
        )
