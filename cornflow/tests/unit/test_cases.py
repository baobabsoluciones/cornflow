"""
Unit test for the cases models and endpoints
"""

# Import from libraries
import json
import jsonpatch


# Import from internal modules
from cornflow.models import CaseModel, ExecutionModel, InstanceModel, UserModel
from cornflow.shared.utils import hash_json_256
from cornflow.tests.const import (
    INSTANCE_URL,
    INSTANCES_LIST,
    INSTANCE_PATH,
    EXECUTION_PATH,
    EXECUTION_URL_NORUN,
    CASE_INSTANCE_URL,
    CASE_URL,
    CASE_PATH,
    CASES_LIST,
    JSON_PATCH_GOOD_PATH,
    JSON_PATCH_BAD_PATH,
    FULL_CASE_LIST,
    FULL_CASE_JSON_PATCH_1,
)
from cornflow.tests.custom_test_case import CustomTestCase, BaseTestCases


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
        self.url = CASE_URL
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
        new_case = self.create_new_row(
            self.url + str(self.case_id) + "/copy/", self.model, {}, check_payload=False
        )
        user = UserModel.get_one_user(self.user)

        original_case = CaseModel.get_one_object_from_user(user, self.case_id)
        new_case = CaseModel.get_one_object_from_user(user, new_case["id"])

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


class TestCaseDetailEndpoint(BaseTestCases.DetailEndpoint):
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


class TestCaseToInstanceEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.payload = self.load_file(CASE_PATH)
        self.model = CaseModel
        self.case_id = self.create_new_row(CASE_URL, self.model, self.payload)
        self.response_items = {
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "executions",
            "data_hash",
            "schema",
        }

    def test_case_to_new_instance(self):
        response = self.client.post(
            CASE_URL + str(self.case_id) + "/instance/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        payload = response.json
        result = self.get_one_row(INSTANCE_URL + payload["id"] + "/", payload)
        dif = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(dif), 0)

        self.items_to_check = ["id", "name", "data", "data_hash", "schema"]
        self.response_items = set(self.items_to_check)

        result = self.get_one_row(INSTANCE_URL + payload["id"] + "/data/", payload)
        dif = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(dif), 0)

    def test_case_does_not_exist(self):
        response = self.client.post(
            CASE_URL + str(2) + "/instance/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"], "The object does not exist")


class TestCaseJsonPatch(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.payload = self.load_file(CASE_PATH)
        self.model = CaseModel
        self.case_id = self.create_new_row(CASE_URL, self.model, self.payload)
        self.payloads = [self.load_file(f) for f in CASES_LIST]
        self.items_to_check = ["name", "description", "path", "schema"]
        self.url = CASE_URL
        self.patch = {
            "patch": jsonpatch.make_patch(
                self.payloads[0]["data"], self.payloads[1]["data"]
            ).patch
        }
        self.patch_file = self.load_file(JSON_PATCH_GOOD_PATH)

    def test_json_patch(self):
        self.patch_row(
            self.url + str(self.case_id) + "/data/",
            self.patch,
            self.payloads[1]["data"],
        )

    def test_json_patch_file(self):
        self.patch_row(
            self.url + str(self.case_id) + "/data/",
            self.patch_file,
            self.payloads[1]["data"],
        )

    def test_not_valid_json_patch(self):
        payload = {"patch": "Not a valid patch"}
        self.patch_row(
            self.url + str(self.case_id) + "/data/",
            payload,
            {},
            expected_status=400,
            check_payload=False,
        )

    def test_not_valid_json_patch_2(self):
        payload = {"some_key": "some_value"}
        self.patch_row(
            self.url + str(self.case_id) + "/data/",
            payload,
            {},
            expected_status=400,
            check_payload=False,
        )

    def test_not_valid_json_patch_3(self):
        patch = {
            "patch": jsonpatch.make_patch(self.payloads[0], self.payloads[1]).patch
        }
        self.patch_row(
            self.url + str(self.case_id) + "/data/",
            patch,
            {},
            expected_status=400,
            check_payload=False,
        )

    def test_not_valid_json_patch_4(self):
        patch = self.load_file(JSON_PATCH_BAD_PATH)
        self.patch_row(
            self.url + str(self.case_id) + "/data/",
            patch,
            {},
            expected_status=400,
            check_payload=False,
        )

    def test_patch_non_existing_case(self):
        self.patch_row(
            self.url + str(500) + "/data/",
            self.patch,
            {},
            expected_status=404,
            check_payload=False,
        )

    def test_patch_created_properly(self):
        self.assertEqual(len(self.patch_file["patch"]), len(self.patch["patch"]))

    def test_patch_not_created_properly(self):
        # Compares the number of operations, not the operations themselves
        self.assertNotEqual(
            len(self.patch_file["patch"]),
            len(jsonpatch.make_patch(self.payloads[0], self.payloads[1]).patch),
        )

        # Compares the number of operations, not the operations themselves
        patch = self.load_file(JSON_PATCH_BAD_PATH)
        self.assertNotEqual(len(patch["patch"]), len(self.patch["patch"]))


class TestCaseCompare(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.payloads = [self.load_file(f) for f in FULL_CASE_LIST]
        self.url = CASE_URL
        self.model = CaseModel
        self.cases_id = [
            self.create_new_row(self.url, self.model, p) for p in self.payloads
        ]
        self.items_to_check = ["name", "description", "path", "schema"]

    def test_get_full_patch(self):
        response = self.client.get(
            self.url + str(self.cases_id[0]) + "/" + str(self.cases_id[1]) + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        payload = self.load_file(FULL_CASE_JSON_PATCH_1)
        self.assertEqual(payload, response.json)
        self.assertEqual(200, response.status_code)

    def test_same_case_error(self):
        response = self.client.get(
            self.url + str(self.cases_id[0]) + "/" + str(self.cases_id[0]) + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(400, response.status_code)

    def test_get_only_data(self):
        response = self.client.get(
            self.url
            + str(self.cases_id[0])
            + "/"
            + str(self.cases_id[1])
            + "/?solution=0",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        payload = self.load_file(FULL_CASE_JSON_PATCH_1)
        payload.pop("solution_patch")
        self.assertEqual(payload, response.json)
        self.assertEqual(200, response.status_code)

    def test_get_only_solution(self):
        response = self.client.get(
            self.url + str(self.cases_id[0]) + "/" + str(self.cases_id[1]) + "/?data=0",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        payload = self.load_file(FULL_CASE_JSON_PATCH_1)
        payload.pop("data_patch")
        self.assertEqual(payload, response.json)
        self.assertEqual(200, response.status_code)

    def test_patch_not_symmetric(self):
        response = self.client.get(
            self.url + str(self.cases_id[1]) + "/" + str(self.cases_id[0]) + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        payload = self.load_file(FULL_CASE_JSON_PATCH_1)
        self.assertNotEqual(payload, response.json)
        self.assertEqual(200, response.status_code)

    def test_case_does_not_exist(self):
        response = self.client.get(
            self.url + str(self.cases_id[0]) + "/" + str(500) + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(404, response.status_code)

        response = self.client.get(
            self.url + str(400) + "/" + str(self.cases_id[0]) + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(404, response.status_code)
