"""
Unit tests for the cases models and endpoints.

This module contains tests for the cases functionality, including:
- Case model operations and relationships
- Case API endpoints
- Case data manipulation and validation
- Case tree structure management

Classes
-------
TestCasesModels
    Tests for the case model functionality and relationships
TestCasesFromInstanceExecutionEndpoint
    Tests for creating cases from instances and executions
TestCasesRawDataEndpoint
    Tests for handling raw case data
TestCaseCopyEndpoint
    Tests for case copying functionality
TestCaseListEndpoint
    Tests for case listing functionality
TestCaseDetailEndpoint
    Tests for case detail operations
TestCaseToInstanceEndpoint
    Tests for converting cases to instances
TestCaseJsonPatch
    Tests for JSON patch operations on cases
TestCaseDataEndpoint
    Tests for case data operations
TestCaseCompare
    Tests for case comparison functionality
"""

# Import from libraries
import copy

from cornflow_client import get_pulp_jsonschema
import json
import jsonpatch
import zlib


# Import from internal modules
from cornflow.models import CaseModel, ExecutionModel, InstanceModel, UserModel
from cornflow.shared.const import DATA_DOES_NOT_EXIST_MSG
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
    """
    Test cases for the case model functionality.

    This class tests the core case model operations including:
    - Case creation and relationships
    - Case tree structure management
    - Case deletion and cascading effects
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes test data including:
        - Base test case setup
        - Test case data and relationships
        - Case tree structure
        """
        super().setUp()

        def load_file(_file):
            with open(_file) as f:
                temp = json.load(f)
            return temp

        self.payload = load_file(INSTANCE_PATH)
        self.payloads = [load_file(f) for f in INSTANCES_LIST]
        parents = [None, 1, 1, 3, 3, 3, 1, 7, 7, 9, 7]
        data = {**self.payload, **dict(user_id=self.user.id)}
        for parent in parents:
            if parent is not None:
                parent = CaseModel.get_one_object(user=self.user, idx=parent)
            node = CaseModel(data=data, parent=parent)
            node.save()

    def test_new_case(self):
        """
        Test creating new cases with parent-child relationships.

        Verifies:
        - Correct path generation for cases
        - Proper parent-child relationships
        """
        case = CaseModel.get_one_object(user=self.user, idx=6)
        self.assertEqual(case.path, "1/3/")
        case = CaseModel.get_one_object(user=self.user, idx=11)
        self.assertEqual(case.path, "1/7/")

    def test_move_case(self):
        """
        Test moving cases within the case tree.

        Verifies:
        - Cases can be moved to new parents
        - Path updates correctly after move
        """
        case6 = CaseModel.get_one_object(user=self.user, idx=6)
        case11 = CaseModel.get_one_object(user=self.user, idx=11)
        case6.move_to(case11)
        self.assertEqual(case6.path, "1/7/11/")

    def test_move_case2(self):
        """
        Test complex case movement scenarios.

        Verifies:
        - Multiple case movements
        - Nested path updates
        - Path integrity after moves
        """
        case3 = CaseModel.get_one_object(user=self.user, idx=3)
        case11 = CaseModel.get_one_object(user=self.user, idx=11)
        case9 = CaseModel.get_one_object(user=self.user, idx=9)
        case10 = CaseModel.get_one_object(user=self.user, idx=10)
        case3.move_to(case11)
        case9.move_to(case3)
        self.assertEqual(case10.path, "1/7/11/3/9/")

    def test_delete_case(self):
        """
        Test case deletion with cascading effects.

        Verifies:
        - Case deletion removes the case
        - Child cases are properly handled
        """
        case7 = CaseModel.get_one_object(user=self.user, idx=7)
        case7.delete()
        case11 = CaseModel.get_one_object(user=self.user, idx=11)
        self.assertIsNone(case11)

    def test_descendants(self):
        """
        Test retrieval of case descendants.

        Verifies:
        - Correct counting of descendants
        - Proper descendant relationships
        """
        case7 = CaseModel.get_one_object(user=self.user, idx=7)
        self.assertEqual(len(case7.descendants), 4)

    def test_depth(self):
        """
        Test case depth calculation.

        Verifies:
        - Correct depth calculation in case tree
        - Proper nesting level determination
        """
        case10 = CaseModel.get_one_object(user=self.user, idx=10)
        self.assertEqual(case10.depth, 4)


class TestCasesFromInstanceExecutionEndpoint(CustomTestCase):
    """
    Test cases for creating cases from instances and executions.

    This class tests the functionality of:
    - Creating cases from existing instances
    - Creating cases from executions
    - Validating case data from different sources
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes:
        - Test instance and execution data
        - API endpoints and models
        - Response validation parameters
        """
        super().setUp()

        payload = self.load_file(INSTANCE_PATH)
        instance_id = self.create_new_row(INSTANCE_URL, InstanceModel, payload=payload)

        payload = self.load_file(EXECUTION_PATH, "instance_id", instance_id)
        execution_id = self.create_new_row(
            EXECUTION_URL_NORUN, ExecutionModel, payload=payload
        )

        self.url = CASE_INSTANCE_URL
        self.model = CaseModel
        self.items_to_check = ["name", "description", "schema"]
        self.response_items = [
            "name",
            "description",
            "data",
            "data_hash",
            "schema",
            "solution",
            "solution_hash",
            "user_id",
            "indicators",
        ]

        self.payload = {
            "name": "testcase",
            "description": "test case for unit tests",
            "instance_id": instance_id,
            "execution_id": execution_id,
            "schema": "solve_model_dag",
        }
        self.instance = InstanceModel.get_one_object(user=self.user, idx=instance_id)
        self.execution = ExecutionModel.get_one_object(user=self.user, idx=execution_id)

    def test_new_case_execution(self):
        """
        Test creating a new case from an execution.

        Verifies:
        - Case creation from execution data
        - Proper data and solution mapping
        - Correct metadata assignment
        """
        self.payload.pop("instance_id")

        case_id = self.create_new_row(self.url, self.model, self.payload)

        created_case = self.client.get(
            f"{CASE_URL}{case_id}/data",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.payload["data"] = self.instance.data
        self.payload["data_hash"] = self.instance.data_hash
        self.payload["schema"] = self.instance.schema
        self.payload["solution"] = self.execution.data
        self.payload["solution_hash"] = self.execution.data_hash
        self.payload["user_id"] = self.user.id
        self.payload["indicators"] = ""

        for key in self.response_items:
            self.assertEqual(self.payload[key], created_case.json[key])

    def test_new_case_instance(self):
        """
        Test creating a new case from an instance.

        Verifies:
        - Case creation from instance data
        - Proper data mapping
        - Correct handling of missing solution
        """
        self.payload.pop("execution_id")
        case_id = self.create_new_row(self.url, self.model, self.payload)

        created_case = self.client.get(
            f"{CASE_URL}{case_id}/data",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.payload["data"] = self.instance.data
        self.payload["data_hash"] = self.instance.data_hash
        self.payload["schema"] = self.instance.schema
        self.payload["user_id"] = self.user.id
        self.payload["solution"] = None
        self.payload["solution_hash"] = hash_json_256(None)
        self.payload["indicators"] = ""
        for key in self.response_items:
            self.assertEqual(self.payload[key], created_case.json[key])

    def test_case_not_created(self):
        """
        Test case creation failure scenarios.

        Verifies proper error handling when case creation fails.
        """
        self.create_new_row(
            self.url, self.model, self.payload, expected_status=400, check_payload=False
        )


class TestCasesRawDataEndpoint(CustomTestCase):
    """
    Test cases for handling raw case data operations.

    This class tests the functionality of:
    - Creating cases with raw data
    - Handling cases with and without solutions
    - Managing case parent-child relationships
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes:
        - Test case data
        - API endpoints
        - Test model configuration
        """
        super().setUp()
        self.payload = self.load_file(CASE_PATH)
        self.url = CASE_URL
        self.model = CaseModel
        self.items_to_check = ["name", "description", "schema"]

    def test_new_case(self):
        """
        Test creating a new case with raw data.

        Verifies:
        - Case creation with complete data
        - Solution data handling
        """
        self.items_to_check = ["name", "description", "schema", "data", "solution"]
        self.payload["solution"] = self.payload["data"]
        self.create_new_row(self.url, self.model, self.payload)

    def test_new_case_without_solution(self):
        """
        Test creating a case without solution data.

        Verifies:
        - Case creation without solution
        - Proper handling of missing solution fields
        - Correct response structure
        """
        self.payload.pop("solution")
        self.items_to_check = ["name", "description", "schema", "data"]
        _id = self.create_new_row(self.url, self.model, self.payload)
        keys_to_check = [
            "data",
            "solution_checks",
            "updated_at",
            "id",
            "schema",
            "data_hash",
            "path",
            "solution_hash",
            "user_id",
            "indicators",
            "solution",
            "is_dir",
            "description",
            "name",
            "checks",
            "created_at",
        ]
        data = self.get_one_row(
            self.url + "/" + str(_id) + "/data/",
            payload={},
            check_payload=False,
            keys_to_check=keys_to_check,
        )
        self.assertIsNone(data["solution"])

    def test_case_with_parent(self):
        """
        Test creating cases with parent-child relationships.

        Verifies:
        - Case creation with parent reference
        - Proper path generation
        - Correct relationship establishment
        """
        payload = dict(self.payload)
        payload.pop("data")
        case_id = self.create_new_row(self.url, self.model, payload)
        payload = dict(self.payload)
        payload["parent_id"] = case_id
        self.create_new_row(self.url, self.model, payload)
        cases = self.client.get(
            self.url,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        result = [(p["id"], p["path"]) for p in cases.json]
        diff = {(2, "1/"), (1, "")}.symmetric_difference(result)
        self.assertEqual(len(diff), 0)

    def test_case_with_bad_parent(self):
        """
        Test case creation with invalid parent reference.

        Verifies proper error handling for non-existent parent cases.
        """
        payload = dict(self.payload)
        payload["parent_id"] = 1
        self.create_new_row(
            self.url, self.model, payload, expected_status=404, check_payload=False
        )

    def test_case_with_case_parent(self):
        """
        Test case creation with invalid parent type.

        Verifies proper error handling when using invalid parent references.
        """
        case_id = self.create_new_row(self.url, self.model, self.payload)
        payload = dict(self.payload)
        payload["parent_id"] = case_id
        self.create_new_row(
            self.url, self.model, payload, expected_status=400, check_payload=False
        )


class TestCaseCopyEndpoint(CustomTestCase):
    """
    Test cases for case copying functionality.

    This class tests the functionality of:
    - Copying existing cases
    - Validating copied case data
    - Handling metadata in copied cases
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes:
        - Source case data
        - Copy operation parameters
        - Validation fields
        """
        super().setUp()
        payload = self.load_file(CASE_PATH)
        self.model = CaseModel
        self.items_to_check = ["name", "description", "schema"]
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
        """
        Test copying a case.

        Verifies:
        - Successful case duplication
        - Correct copying of case attributes
        - Proper handling of modified and new attributes
        """
        new_case = self.create_new_row(
            self.url + str(self.case_id) + "/copy/", self.model, {}, check_payload=False
        )

        original_case = CaseModel.get_one_object(user=self.user, idx=self.case_id)
        new_case = CaseModel.get_one_object(user=self.user, idx=new_case["id"])

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
    """
    Test cases for case listing functionality.

    This class tests the functionality of:
    - Retrieving case listings
    - Applying filters to case lists
    - Validating case list responses
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes:
        - Test case data
        - List operation parameters
        - Response validation fields
        """
        super().setUp()
        self.payload = self.load_file(CASE_PATH)
        self.payloads = [self.load_file(f) for f in CASES_LIST]
        self.model = CaseModel
        self.items_to_check = ["name", "description", "path", "schema"]
        self.url = CASE_URL

    def test_get_rows(self):
        """
        Test retrieving multiple cases.

        Verifies:
        - Successful retrieval of case listings
        - Proper response structure
        - Correct field validation
        """
        keys_to_check = [
            "data_hash",
            "created_at",
            "is_dir",
            "path",
            "schema",
            "description",
            "solution_hash",
            "id",
            "user_id",
            "updated_at",
            "name",
            "indicators",
        ]
        self.get_rows(self.url, self.payloads, keys_to_check=keys_to_check)


class TestCaseDetailEndpoint(BaseTestCases.DetailEndpoint):
    """
    Test cases for case detail operations.

    This class tests the functionality of:
    - Retrieving individual case details
    - Updating case information
    - Handling case deletion
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes:
        - Test case data
        - Detail operation parameters
        - Response validation fields
        """
        super().setUp()
        self.payload = self.load_file(CASE_PATH)
        self.model = CaseModel
        self.items_to_check = [
            "name",
            "description",
            "schema",
            "data_hash",
            "solution_hash",
        ]
        self.response_items = {
            "id",
            "name",
            "description",
            "path",
            "is_dir",
            "schema",
            "data_hash",
            "solution_hash",
            "created_at",
            "updated_at",
            "user_id",
            "indicators",
        }
        self.url = CASE_URL

    def test_delete_children(self):
        """
        Test case deletion with child cases.

        Verifies:
        - Successful deletion of parent case
        - Proper handling of child cases
        - Cascade deletion behavior
        """
        payload = dict(self.payload)
        payload.pop("data")
        case_id = self.create_new_row(self.url, self.model, payload)
        payload = dict(self.payload)
        payload["parent_id"] = case_id
        self.create_new_row(self.url, self.model, payload)
        self.delete_row(self.url + str(case_id) + "/")
        cases = self.client.get(
            self.url,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(len(cases.json), 0)


class TestCaseToInstanceEndpoint(CustomTestCase):
    """
    Test cases for converting cases to instances.

    This class tests the functionality of:
    - Converting cases to instances
    - Validating converted instance data
    - Handling conversion errors
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes:
        - Test case data
        - Conversion parameters
        - Response validation fields
        """
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
        """
        Test converting a case to a new instance.

        Verifies:
        - Successful case to instance conversion
        - Proper data mapping
        - Correct response structure
        """
        response = self.client.post(
            CASE_URL + str(self.case_id) + "/instance/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        payload = response.json
        keys_to_check = [
            "id",
            "schema",
            "data_hash",
            "executions",
            "user_id",
            "description",
            "name",
            "created_at",
        ]
        result = self.get_one_row(
            INSTANCE_URL + payload["id"] + "/", payload, keys_to_check=keys_to_check
        )
        diff = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(diff), 0)

        self.items_to_check = [
            "id",
            "name",
            "data",
            "checks",
            "data_hash",
            "schema",
            "user_id",
            "created_at",
            "description",
        ]
        self.response_items = set(self.items_to_check)

        keys_to_check = [
            "data",
            "id",
            "schema",
            "data_hash",
            "user_id",
            "description",
            "name",
            "checks",
            "created_at",
        ]

        result = self.get_one_row(
            INSTANCE_URL + payload["id"] + "/data/",
            payload,
            keys_to_check=keys_to_check,
        )
        dif = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(dif), 0)

    def test_case_does_not_exist(self):
        """
        Test conversion of non-existent case.

        Verifies proper error handling when converting non-existent cases.
        """
        response = self.client.post(
            CASE_URL + str(2) + "/instance/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"], DATA_DOES_NOT_EXIST_MSG)


class TestCaseJsonPatch(CustomTestCase):
    """
    Test cases for JSON patch operations on cases.

    This class tests the functionality of:
    - Applying JSON patches to cases
    - Validating patched case data
    - Handling patch errors
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes:
        - Test case data
        - Patch operation parameters
        - Test payloads
        """
        super().setUp()
        self.payload = self.load_file(CASE_PATH)
        self.model = CaseModel
        self.case_id = self.create_new_row(CASE_URL, self.model, self.payload)
        self.payloads = [self.load_file(f) for f in CASES_LIST]
        self.items_to_check = ["name", "description", "schema"]
        self.url = CASE_URL
        self.patch = dict(
            data_patch=jsonpatch.make_patch(
                self.payloads[0]["data"], self.payloads[1]["data"]
            ).patch
        )
        self.patch_file = self.load_file(JSON_PATCH_GOOD_PATH)

    def test_json_patch(self):
        """
        Test applying a JSON patch to a case.

        Verifies:
        - Successful patch application
        - Correct data transformation
        - Proper validation of patched data
        """
        self.patch_row(
            self.url + str(self.case_id) + "/data/",
            self.patch,
            self.payloads[1],
        )

        row = self.client.get(
            self.url + str(self.case_id) + "/data/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertIsNone(row.json["checks"])

    def test_json_patch_complete(self):
        """
        Test applying a complete JSON patch.

        Verifies:
        - Complex patch operations
        - Data and solution patching
        - Response validation
        """
        original = self.load_file(FULL_CASE_LIST[0])
        original["data"] = get_pulp_jsonschema("../tests/data/gc_input.json")
        original["solution"] = get_pulp_jsonschema("../tests/data/gc_output.json")

        modified = copy.deepcopy(original)
        modify_data_solution(modified)

        case_id = self.create_new_row(self.url, self.model, original)
        payload = self.load_file(FULL_CASE_JSON_PATCH_1)
        self.patch_row(
            self.url + str(case_id) + "/data/",
            payload,
            modified,
        )
        row = self.client.get(
            self.url + str(case_id) + "/data/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertIsNone(row.json["checks"])
        self.assertIsNone(row.json["solution_checks"])

    def test_json_patch_file(self):
        """
        Test applying a JSON patch from a file.

        Verifies successful patch application from file source.
        """
        self.patch_row(
            self.url + str(self.case_id) + "/data/",
            self.patch_file,
            self.payloads[1],
        )

    def test_not_valid_json_patch(self):
        """
        Test handling of invalid JSON patches.

        Verifies proper error handling for malformed patches.
        """
        payload = {"patch": "Not a valid patch"}
        self.patch_row(
            self.url + str(self.case_id) + "/data/",
            payload,
            {},
            expected_status=400,
            check_payload=False,
        )

    def test_not_valid_json_patch_2(self):
        """
        Test handling of invalid JSON patch structure.

        Verifies proper error handling for patches with invalid structure.
        """
        payload = {"some_key": "some_value"}
        self.patch_row(
            self.url + str(self.case_id) + "/data/",
            payload,
            {},
            expected_status=400,
            check_payload=False,
        )

    def test_not_valid_json_patch_3(self):
        """
        Test handling of invalid patch operations.

        Verifies proper error handling for invalid patch operations.
        """
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
        """
        Test handling of bad patch file content.

        Verifies proper error handling for invalid patch file content.
        """
        patch = self.load_file(JSON_PATCH_BAD_PATH)
        self.patch_row(
            self.url + str(self.case_id) + "/data/",
            patch,
            {},
            expected_status=400,
            check_payload=False,
        )

    def test_patch_non_existing_case(self):
        """
        Test patching non-existent case.

        Verifies proper error handling when patching non-existent cases.
        """
        self.patch_row(
            self.url + str(500) + "/data/",
            self.patch,
            {},
            expected_status=404,
            check_payload=False,
        )

    def test_patch_created_properly(self):
        """
        Test proper patch creation.

        Verifies correct patch generation and structure.
        """
        self.assertEqual(
            len(self.patch_file["data_patch"]), len(self.patch["data_patch"])
        )

    def test_patch_not_created_properly(self):
        """
        Test improper patch creation scenarios.

        Verifies detection of improperly created patches.
        """
        self.assertNotEqual(
            len(self.patch_file["data_patch"]),
            len(jsonpatch.make_patch(self.payloads[0], self.payloads[1]).patch),
        )

        patch = self.load_file(JSON_PATCH_BAD_PATH)
        self.assertNotEqual(len(patch["data_patch"]), len(self.patch["data_patch"]))


class TestCaseDataEndpoint(CustomTestCase):
    """
    Test cases for case data operations.

    This class tests the functionality of:
    - Retrieving case data
    - Handling compressed data
    - Validating data responses
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes:
        - Test case data
        - Data operation parameters
        - Response validation fields
        """
        super().setUp()
        self.payload = self.load_file(CASE_PATH)
        self.model = CaseModel
        self.payload["id"] = self.create_new_row(CASE_URL, self.model, self.payload)
        self.url = CASE_URL
        self.items_to_check = [
            "name",
            "description",
            "schema",
            "data",
        ]

    def test_get_data(self):
        """
        Test retrieving case data.

        Verifies:
        - Successful data retrieval
        - Proper response structure
        - Field validation
        """
        keys_to_check = [
            "data",
            "solution_checks",
            "updated_at",
            "id",
            "schema",
            "data_hash",
            "path",
            "solution_hash",
            "user_id",
            "indicators",
            "solution",
            "is_dir",
            "description",
            "name",
            "checks",
            "created_at",
        ]
        self.get_one_row(
            self.url + str(self.payload["id"]) + "/data/",
            self.payload,
            keys_to_check=keys_to_check,
        )

    def test_get_no_data(self):
        """
        Test retrieving non-existent case data.

        Verifies proper error handling for non-existent cases.
        """
        self.get_one_row(
            self.url + str(500) + "/data/",
            {},
            expected_status=404,
            check_payload=False,
            keys_to_check=["error"],
        )

    def test_get_compressed_data(self):
        """
        Test retrieving compressed case data.

        Verifies:
        - Successful compression
        - Proper decompression
        - Data integrity
        """
        headers = self.get_header_with_auth(self.token)
        headers["Accept-Encoding"] = "gzip"

        response = self.client.get(
            self.url + str(self.payload["id"]) + "/data/", headers=headers
        )
        self.assertEqual(response.headers["Content-Encoding"], "gzip")
        raw = zlib.decompress(response.data, 16 + zlib.MAX_WBITS).decode("utf-8")
        response = json.loads(raw)
        for i in self.items_to_check:
            self.assertEqual(self.payload[i], response[i])


class TestCaseCompare(CustomTestCase):
    """
    Test cases for case comparison functionality.

    This class tests the functionality of:
    - Comparing different cases
    - Generating comparison patches
    - Handling comparison errors
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes:
        - Test cases for comparison
        - Comparison parameters
        - Validation fields
        """
        super().setUp()
        self.payloads = [self.load_file(f) for f in FULL_CASE_LIST]
        self.payloads[0]["data"] = get_pulp_jsonschema("../tests/data/gc_input.json")
        self.payloads[0]["solution"] = get_pulp_jsonschema(
            "../tests/data/gc_output.json"
        )
        self.payloads[1] = copy.deepcopy(self.payloads[0])
        modify_data_solution(self.payloads[1])

        self.url = CASE_URL
        self.model = CaseModel
        self.cases_id = [
            self.create_new_row(self.url, self.model, p) for p in self.payloads
        ]

        self.items_to_check = ["name", "description", "schema"]

    def test_get_full_patch(self):
        """
        Test generating full comparison patch.

        Verifies:
        - Successful patch generation
        - Correct patch structure
        - Proper response format
        """
        response = self.client.get(
            self.url + str(self.cases_id[0]) + "/" + str(self.cases_id[1]) + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        payload = self.load_file(FULL_CASE_JSON_PATCH_1)
        self.assertEqual(payload, response.json)
        self.assertEqual(200, response.status_code)

    def test_same_case_error(self):
        """
        Test comparing a case with itself.

        Verifies proper error handling for self-comparison.
        """
        response = self.client.get(
            self.url + str(self.cases_id[0]) + "/" + str(self.cases_id[0]) + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(400, response.status_code)

    def test_get_only_data(self):
        """
        Test comparing only case data.

        Verifies:
        - Data-only comparison
        - Proper exclusion of solution
        - Correct response format
        """
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
        """
        Test comparing only case solutions.

        Verifies:
        - Solution-only comparison
        - Proper exclusion of data
        - Correct response format
        """
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
        """
        Test patch asymmetry.

        Verifies that patches are direction-dependent.
        """
        response = self.client.get(
            self.url + str(self.cases_id[1]) + "/" + str(self.cases_id[0]) + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        payload = self.load_file(FULL_CASE_JSON_PATCH_1)
        self.assertNotEqual(payload, response.json)
        self.assertEqual(200, response.status_code)

    def test_case_does_not_exist(self):
        """
        Test comparing with non-existent case.

        Verifies proper error handling for non-existent cases.
        """
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

    def test_get_patch_and_apply(self):
        """
        Test generating and applying a patch.

        Verifies:
        - Patch generation
        - Successful patch application
        - Data consistency
        """
        response = self.client.get(
            self.url + str(self.cases_id[0]) + "/" + str(self.cases_id[1]) + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        case_to_compare = self.client.get(
            self.url + str(self.cases_id[1]) + "/data/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.patch_row(
            self.url + str(self.cases_id[0]) + "/data/",
            response.json,
            case_to_compare.json,
        )

    def test_case_compare_compression(self):
        """
        Test case comparison with compression.

        Verifies:
        - Successful compression
        - Proper decompression
        - Data integrity
        """
        headers = self.get_header_with_auth(self.token)
        headers["Accept-Encoding"] = "gzip"
        response = self.client.get(
            self.url + str(self.cases_id[0]) + "/" + str(self.cases_id[1]) + "/",
            follow_redirects=True,
            headers=headers,
        )

        self.assertEqual(response.headers["Content-Encoding"], "gzip")
        raw = zlib.decompress(response.data, 16 + zlib.MAX_WBITS).decode("utf-8")
        response = json.loads(raw)
        payload = self.load_file(FULL_CASE_JSON_PATCH_1)
        self.assertEqual(payload, response)


def modify_data(data):
    """
    Modify test case data.

    Helper function to modify case data for testing.
    """
    data["pairs"][16]["n2"] = 10
    data["pairs"][27]["n2"] = 3
    data["pairs"][30]["n1"] = 6
    data["pairs"][50]["n2"] = 14
    data["pairs"][56]["n1"] = 11
    data["pairs"][83]["n2"] = 37
    data["pairs"][103]["n1"] = 26


def modify_solution(solution):
    """
    Modify test case solution.

    Helper function to modify case solution for testing.
    """
    solution["assignment"][4]["color"] = 3
    solution["assignment"][7]["color"] = 2
    solution["assignment"][24]["color"] = 1
    solution["assignment"][42]["color"] = 3


def modify_data_solution(data):
    """
    Modify both test case data and solution.

    Helper function to modify both case data and solution for testing.
    """
    modify_data(data["data"])
    modify_solution(data["solution"])
    return data
