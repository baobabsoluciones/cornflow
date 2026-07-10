# Imports from external libraries
from cornflow.commands import access_init_command, register_dag_permissions_command
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import UserModel
from cornflow.models.meta_models import EmptyBaseModel
from cornflow.shared import db
from cornflow.shared.authentication import Auth
from cornflow.shared.const import ALL_DEFAULT_ROLES, ADMIN_ROLE, PLANNER_ROLE
from cornflow.tests.custom_test_case import CustomTestCase
from flask import current_app
from flask_restful import Api
from flask_apispec import use_kwargs, marshal_with

import json
import logging as log
import types
from unittest.mock import patch

# Imports from internal modules
from cornflow.app import create_app
from cornflow.endpoints import resources
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.tests.const import FRONTEND_AUTOMATION_URL, LOGIN_URL, SIGNUP_URL
from cornflow.tests.unit.tools_frontend_automation import (
    TestModelSchema,
    TEST_MODEL_JSONSCHEMA,
    FrontendTableWithoutGroup,
    FrontendTableWithGroup,
    FrontendTableWithSection,
    FrontendTableWithGroupAndSection,
    FrontendTableWithSchemas,
    FrontendTableWithSchemaDag,
    FrontendTableWithSchemaTwoDag,
    FrontendTableWithUnknownSchema,
    FrontendTableWithMixedSchemas,
)
from cornflow.shared.frontend_automation import automate_frontend, EndpointTypes


class FrontendAutomationTestCase(CustomTestCase):
    """
    Test case for the FrontendAutomationEndpoint.
    """

    def set_up_app(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()
            access_init_command(verbose=False)

            register_deployed_dags_command_test(verbose=True)

    def setUp(self):
        # `resources` is a module-level list. Tests (and the endpoint itself, when it
        # discovers plugin/external resources) append to it, so snapshot it now and
        # restore it in tearDown to keep tests independent.
        self._original_resources = list(resources)

        # NOTE: do NOT recreate the app here. flask_testing's _pre_setup already created
        # self.app via create_app() and bound self.client to it. Reassigning self.app to a
        # second app would leave self.client pointing at the first one, so endpoints
        # registered later via _add_endpoint_to_app (Api(self.app)) would land on a different
        # app than the one serving requests, causing flask_apispec's converter to raise
        # KeyError: '<endpoint>' when looking it up in url_map._rules_by_endpoint.
        self.set_up_app()

        self.models_to_clean = []
        self.tearDown()

        log.root.setLevel(current_app.config["LOG_LEVEL"])

        self.token = self.create_user_with_role(PLANNER_ROLE)

        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )
        data = Auth().decode_token(self.token)
        user_object = UserModel.get_one_object(username=data["sub"])
        self.user = user_object.id
        self.url = None
        self.model = None
        self.roles_with_access = []
        self.endpoint = FRONTEND_AUTOMATION_URL
        self.base_sample_endpoint_name = "sample_endpoint"
        self.base_sample_endpoint_url = "/sample-endpoint"
        self.base_sample_table_name = "test_data_model"

    def tearDown(self):
        # Restore the shared resources list in place (preserving its identity, since the
        # endpoint imports the same list object) so each test starts from a clean state.
        original = getattr(self, "_original_resources", None)
        if original is not None:
            resources[:] = original

    @classmethod
    def tearDownClass(cls):
        app = cls.create_app(cls)
        with app.app_context():
            db.drop_all()

    def create_user_with_role(self, role_id):
        """
        Creates a new user and assigns them a specific role.

        :param int role_id: ID of the role to assign
        :returns: Authentication token for the created user
        :rtype: str
        """
        data = {
            "username": "testuser" + str(role_id),
            "email": "testemail" + str(role_id) + "@test.org",
            "password": "Testpassword1!",
        }
        # Check if the user already exists, and if not, create it
        existing_user = UserModel.query.filter_by(email=data["email"]).first()
        if not existing_user:
            response = self.create_user(data)
            self.assign_role(response.json["id"], role_id)

        data.pop("email")
        return self.client.post(
            LOGIN_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]

    def create_user(self, data):
        """
        Creates a new user through the API.

        :param dict data: Dictionary containing user data (username, email, password)
        :returns: API response from user creation
        :rtype: Response
        """
        return self.client.post(
            SIGNUP_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

    def _get_table_endpoint_infos(self, i, is_external=False):
        """
        Get the table endpoint name, url and table name for the given index.
        """
        sample_endpoint_name = f"{self.base_sample_endpoint_name}_{i}"
        sample_endpoint_url = f"{self.base_sample_endpoint_url}_{i}/"
        if is_external:
            sample_endpoint_url = "/external" + sample_endpoint_url
        sample_table_name = f"{self.base_sample_table_name}_{i}"

        return sample_endpoint_name, sample_endpoint_url, sample_table_name

    def _get_model_class(self, table_name, frontend_table=None):
        """
        Dynamically create a model class with the given table name.
        """

        class TestDataModel(EmptyBaseModel):
            __tablename__ = table_name
            __frontend_table__ = frontend_table
            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.String(50), nullable=False)

        return TestDataModel

    def _register_route(self, endpoint_class, name, url):
        """
        Register a resource's route on the app the client is bound to.

        The frontend automation endpoint documents every resource via
        flask_apispec, which looks the endpoint up in ``url_map._rules_by_endpoint``.
        Any resource we want to be automated (whether it comes from the core
        resources list, a plugin or an external app) must therefore have its route
        present in the app's url_map.
        """
        # The app has already served requests during setUp (login/signup), so Flask locks
        # it and refuses add_url_rule ("setup method ... can no longer be called"). Briefly
        # reset the first-request flag so we can register the new test route on the same app
        # the client uses, then restore it.
        was_locked = self.app._got_first_request
        self.app._got_first_request = False
        try:
            api = Api(self.app)
            api.add_resource(endpoint_class, url, endpoint=name)
        finally:
            self.app._got_first_request = was_locked

    def _register_view_and_permission(self, resource):
        """
        Create the ViewModel row and the role permissions for a single resource so
        the requesting user is allowed to see it in the automation output.
        """
        from cornflow.commands.views import (
            get_database_view,
            get_views_to_register,
            load_changes_to_db,
        )
        from cornflow.commands.permissions import (
            get_base_permissions,
            get_db_permissions,
            get_permissions_in_code_as_tuples,
            get_permissions_to_register,
            save_and_delete_permissions,
        )
        from cornflow.models import ViewModel

        with self.app.app_context():
            views_in_db = get_database_view()
            to_register, views_in_db = get_views_to_register([resource], views_in_db)
            load_changes_to_db([], to_register, [])

            views_in_db = {v.name: v.id for v in ViewModel.get_all_objects()}
            roles_with_access = {
                resource["endpoint"]: resource["resource"].ROLES_WITH_ACCESS
            }
            base_perms = get_base_permissions(roles_with_access, {})
            _, permissions_in_db_keys = get_db_permissions()
            tuples = get_permissions_in_code_as_tuples(
                [resource], views_in_db, base_perms, []
            )
            to_register = get_permissions_to_register(tuples, permissions_in_db_keys)
            save_and_delete_permissions(to_register, [])

    def _add_endpoint_to_app(self, endpoint_class, name, url):
        """
        Adds a new endpoint to the Flask app for testing purposes.
        """

        # Add the new resource to the resources list to be able to test the endpoint
        resources.append(
            {
                "resource": endpoint_class,
                "urls": url,
                "endpoint": name,
            }
        )
        self._register_route(endpoint_class, name, url)
        with self.app.app_context():
            access_init_command(verbose=False)

    # def test_frontend_automation_without_arguments(self):
    #     """
    #     Test the automate_frontend decorator:
    #     - without schemas arguments
    #     - without frontend_groups nor frontend_table definitions
    #     """
    #     sample_endpoint_name, sample_endpoint_url, sample_table_name = (
    #         self._get_table_endpoint_infos(1)
    #     )
    #
    #     test_model_class = self._get_model_class(sample_table_name)
    #
    #     class SampleEndpoint(BaseMetaResource):
    #         ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES
    #
    #         def __init__(sf):
    #             super().__init__()
    #             sf.data_model = test_model_class
    #
    #         @automate_frontend(EndpointTypes.DELETE_ITEM)
    #         def delete(self):
    #             return {"message": "Item deleted correctly"}
    #
    #     se = SampleEndpoint()
    #
    #     # Check that the endpoint works correctly
    #     result = se.delete().json
    #     self.assertIsInstance(result, dict)
    #     self.assertIn("message", result)
    #     self.assertEqual(result["message"], "Item deleted correctly")
    #
    #     # Check if the function has the attribute set by the decorator
    #     self.assertTrue(hasattr(se.delete, "__automate_frontend__"))
    #     self.assertEqual(
    #         se.delete.__automate_frontend__["endpoint_type"],
    #         EndpointTypes.DELETE_ITEM.value,
    #     )
    #     # Add the endpoint to the app
    #     self._add_endpoint_to_app(
    #         SampleEndpoint, sample_endpoint_name, sample_endpoint_url
    #     )
    #     # Make a request to the frontend automation endpoint
    #     response = self.client.get(
    #         self.endpoint, headers=self.get_header_with_auth(self.token)
    #     )
    #     # Check that the response is correct
    #     self.assertEqual(response.status_code, 200)
    #     self.assertIsInstance(response.json, dict)
    #     for key in ["paths", "available_automations"]:
    #         self.assertIn(key, response.json)
    #     for key in ["tables", "groups"]:
    #         self.assertIn(key, response.json["available_automations"])
    #     # Check tables
    #     self.assertIn(
    #         test_model_class.__tablename__,
    #         response.json["available_automations"]["tables"],
    #     )
    #     self.assertDictEqual(
    #         response.json["available_automations"]["tables"][
    #             test_model_class.__tablename__
    #         ],
    #         {
    #             "delete_item": {"http_method": "DELETE", "url": sample_endpoint_url},
    #             "group": None,
    #             "icon": None,
    #             "title": sample_table_name,
    #             "section": None,
    #             "order": 0,
    #             "model_table_name": sample_table_name,
    #             "schemas": None,
    #         },
    #     )
    #     # Check paths
    #     self.assertIn(sample_endpoint_url, response.json["paths"])
    #     self.assertDictEqual(
    #         response.json["paths"][sample_endpoint_url],
    #         {"delete": {"parameters": [], "responses": {}}},
    #     )
    #
    # def test_frontend_automation_roles(self):
    #     """
    #     Check that the roles_with_access are correctly taken into account
    #     """
    #     endpoint_name, endpoint_url, table_name = self._get_table_endpoint_infos(2)
    #
    #     test_model_class = self._get_model_class(table_name)
    #
    #     class SampleEndpoint(BaseMetaResource):
    #         ROLES_WITH_ACCESS = [ADMIN_ROLE]
    #
    #         def __init__(sf):
    #             super().__init__()
    #             sf.data_model = test_model_class
    #
    #         @automate_frontend(EndpointTypes.DELETE_ITEM)
    #         def delete(self):
    #             return {"message": "Item deleted correctly"}
    #
    #     se = SampleEndpoint()
    #
    #     # Check that the endpoint works correctly
    #     result = se.delete().json
    #     self.assertIsInstance(result, dict)
    #     self.assertIn("message", result)
    #     self.assertEqual(result["message"], "Item deleted correctly")
    #
    #     # Check if the function has the attribute set by the decorator
    #     self.assertTrue(hasattr(se.delete, "__automate_frontend__"))
    #     self.assertEqual(
    #         se.delete.__automate_frontend__["endpoint_type"],
    #         EndpointTypes.DELETE_ITEM.value,
    #     )
    #
    #     # Add the endpoint to the app
    #     self._add_endpoint_to_app(SampleEndpoint, endpoint_name, endpoint_url)
    #
    #     # Make a request to the frontend automation endpoint
    #     response = self.client.get(
    #         self.endpoint, headers=self.get_header_with_auth(self.token)
    #     )
    #
    #     # Check that the response is correct
    #     self.assertEqual(response.status_code, 200)
    #     self.assertIsInstance(response.json, dict)
    #     for key in ["paths", "available_automations"]:
    #         self.assertIn(key, response.json)
    #     for key in ["tables", "groups"]:
    #         self.assertIn(key, response.json["available_automations"])
    #
    #     # Check tables
    #     self.assertNotIn(
    #         test_model_class.__tablename__,
    #         response.json["available_automations"]["tables"],
    #     )
    #     # Check paths
    #     self.assertNotIn(endpoint_url, response.json["paths"])
    #
    # def test_frontend_automation_use_kwargs(self):
    #     """
    #     Test the automate_frontend decorator with use_kwargs argument
    #     """
    #     endpoint_name, endpoint_url, table_name = self._get_table_endpoint_infos(3)
    #
    #     test_model_class = self._get_model_class(table_name)
    #
    #     class SampleEndpoint(BaseMetaResource):
    #         ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES
    #
    #         def __init__(sf):
    #             super().__init__()
    #             sf.data_model = test_model_class
    #
    #         @automate_frontend(
    #             EndpointTypes.POST_ITEM,
    #         )
    #         @use_kwargs(TestModelSchema)
    #         def post(self, *args, **kwargs):
    #             return {"message": "Item created correctly"}
    #
    #     # Check that the endpoint works correctly
    #     se = SampleEndpoint()
    #     with self.app.test_request_context(
    #         "/external" + endpoint_url,
    #         method="POST",
    #         json={"name": "Test Name", "description": "Test Description"},
    #     ):
    #         result = se.post().json
    #     self.assertIsInstance(result, dict)
    #     self.assertIn("message", result)
    #     self.assertEqual(result["message"], "Item created correctly")
    #     # Check if the function has the attribute set by the decorator
    #     self.assertTrue(hasattr(se.post, "__automate_frontend__"))
    #     self.assertEqual(
    #         se.post.__automate_frontend__["endpoint_type"],
    #         EndpointTypes.POST_ITEM.value,
    #     )
    #     # Add the endpoint to the app
    #     self._add_endpoint_to_app(SampleEndpoint, endpoint_name, endpoint_url)
    #     # Make a request to the frontend automation endpoint
    #     response = self.client.get(
    #         self.endpoint, headers=self.get_header_with_auth(self.token)
    #     )
    #     # Check that the response is correct
    #     self.assertEqual(response.status_code, 200)
    #     self.assertIsInstance(response.json, dict)
    #     for key in ["paths", "available_automations"]:
    #         self.assertIn(key, response.json)
    #     for key in ["tables", "groups"]:
    #         self.assertIn(key, response.json["available_automations"])
    #     # Check tables
    #     self.assertIn(
    #         test_model_class.__tablename__,
    #         response.json["available_automations"]["tables"],
    #     )
    #     self.assertDictEqual(
    #         response.json["available_automations"]["tables"][
    #             test_model_class.__tablename__
    #         ],
    #         {
    #             "post_item": {"http_method": "POST", "url": endpoint_url},
    #             "group": None,
    #             "icon": None,
    #             "title": table_name,
    #             "section": None,
    #             "order": 0,
    #             "model_table_name": table_name,
    #             "schemas": None,
    #         },
    #     )
    #     # Check paths
    #     self.assertIn(endpoint_url, response.json["paths"])
    #     self.assertIn("post", response.json["paths"][endpoint_url])
    #     self.assertIn("parameters", response.json["paths"][endpoint_url]["post"])
    #     self.assertIn("responses", response.json["paths"][endpoint_url]["post"])
    #     # Check that the parameters contain the schema fields
    #     parameters = response.json["paths"][endpoint_url]["post"]["parameters"]
    #     self.assertIsInstance(parameters, list)
    #     self.assertEqual(len(parameters), 1)
    #     parameter = parameters[0]
    #     self.assertIn("in", parameter)
    #     self.assertEqual(parameter["in"], "body")
    #     self.assertIn("schema", parameter)
    #     self.assertIn("$ref", parameter["schema"])
    #     self.assertEqual(
    #         parameter["schema"]["$ref"],
    #         "#/definitions/TestModel",
    #     )
    #     # Check that the schema is in the definitions
    #     self.assertIn("definitions", response.json)
    #     self.assertIn("TestModel", response.json["definitions"])
    #     schema = response.json["definitions"]["TestModel"]
    #     self.assertDictEqual(schema, TEST_MODEL_JSONSCHEMA)
    #
    # def test_frontend_automation_marshal_with(self):
    #     """
    #     Test the automate_frontend decorator with marshal_with argument
    #     """
    #     endpoint_name, endpoint_url, table_name = self._get_table_endpoint_infos(4)
    #
    #     test_model_class = self._get_model_class(table_name)
    #
    #     class SampleEndpoint(BaseMetaResource):
    #         ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES
    #
    #         def __init__(sf):
    #             super().__init__()
    #             sf.data_model = test_model_class
    #
    #         @automate_frontend(
    #             EndpointTypes.GET_ITEM,
    #         )
    #         @marshal_with(TestModelSchema)
    #         def get(self, *args, **kwargs):
    #             return {"id": 1, "name": "Test Name", "description": "Test Description"}
    #
    #     # Check that the endpoint works correctly
    #     se = SampleEndpoint()
    #     with self.app.test_request_context(
    #         "/external" + endpoint_url,
    #         method="GET",
    #     ):
    #         result = se.get().json
    #     self.assertIsInstance(result, dict)
    #     self.assertNotIn("id", result)
    #     self.assertIn("name", result)
    #     self.assertIn("description", result)
    #     self.assertEqual(result["name"], "Test Name")
    #     self.assertEqual(result["description"], "Test Description")
    #     # Check if the function has the attribute set by the decorator
    #     self.assertTrue(hasattr(se.get, "__automate_frontend__"))
    #     self.assertEqual(
    #         se.get.__automate_frontend__["endpoint_type"],
    #         EndpointTypes.GET_ITEM.value,
    #     )
    #     # Add the endpoint to the app
    #     self._add_endpoint_to_app(SampleEndpoint, endpoint_name, endpoint_url)
    #     # Make a request to the frontend automation endpoint
    #     response = self.client.get(
    #         self.endpoint, headers=self.get_header_with_auth(self.token)
    #     )
    #     # Check that the response is correct
    #     self.assertEqual(response.status_code, 200)
    #     self.assertIsInstance(response.json, dict)
    #     for key in ["paths", "available_automations"]:
    #         self.assertIn(key, response.json)
    #     for key in ["tables", "groups"]:
    #         self.assertIn(key, response.json["available_automations"])
    #     # Check tables
    #     self.assertIn(
    #         test_model_class.__tablename__,
    #         response.json["available_automations"]["tables"],
    #     )
    #     self.assertDictEqual(
    #         response.json["available_automations"]["tables"][
    #             test_model_class.__tablename__
    #         ],
    #         {
    #             "get_item": {"http_method": "GET", "url": endpoint_url},
    #             "group": None,
    #             "icon": None,
    #             "title": table_name,
    #             "section": None,
    #             "order": 0,
    #             "model_table_name": table_name,
    #             "schemas": None,
    #         },
    #     )
    #     # Check paths
    #     self.assertIn(endpoint_url, response.json["paths"])
    #     self.assertIn("get", response.json["paths"][endpoint_url])
    #     self.assertIn("parameters", response.json["paths"][endpoint_url]["get"])
    #     self.assertIn("responses", response.json["paths"][endpoint_url]["get"])
    #     # Check that the responses contain the schema fields
    #     responses = response.json["paths"][endpoint_url]["get"]["responses"]
    #     self.assertIsInstance(responses, dict)
    #     self.assertIn("default", responses)
    #     response_200 = responses["default"]
    #     self.assertIn("schema", response_200)
    #     self.assertIn("$ref", response_200["schema"])
    #     self.assertEqual(
    #         response_200["schema"]["$ref"],
    #         "#/definitions/TestModel",
    #     )
    #     # Check that the schema is in the definitions
    #     self.assertIn("definitions", response.json)
    #     self.assertIn("TestModel", response.json["definitions"])
    #     schema = response.json["definitions"]["TestModel"]
    #     self.assertDictEqual(schema, TEST_MODEL_JSONSCHEMA)
    #
    # def test_frontend_automation_request_response_schemas(self):
    #     """
    #     Test the automate_frontend decorator with request and response schemas arguments
    #     """
    #     endpoint_name, endpoint_url, table_name = self._get_table_endpoint_infos(5)
    #
    #     test_model_class = self._get_model_class(table_name)
    #
    #     class SampleEndpoint(BaseMetaResource):
    #         ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES
    #
    #         def __init__(sf):
    #             super().__init__()
    #             sf.data_model = test_model_class
    #
    #         @automate_frontend(
    #             EndpointTypes.POST_ITEM,
    #             schema_request=TestModelSchema,
    #             schema_response=TestModelSchema,
    #         )
    #         def post(self, *args, **kwargs):
    #             return {"error": "Not implemented"}, 400
    #
    #     # Check that the endpoint works correctly
    #     se = SampleEndpoint()
    #     with self.app.test_request_context(
    #         "/external" + endpoint_url,
    #         method="POST",
    #         json={"name": "Test Name", "description": "Test Description"},
    #     ):
    #         result = se.post().json
    #
    #     self.assertIsInstance(result, dict)
    #     # Check that the response contains the error message, since we're not using
    #     #    marshal_with to format the response
    #     self.assertIn("error", result)
    #     self.assertEqual(result["error"], "Not implemented")
    #     # Check if the function has the attribute set by the decorator
    #     self.assertTrue(hasattr(se.post, "__automate_frontend__"))
    #     self.assertEqual(
    #         se.post.__automate_frontend__["endpoint_type"],
    #         EndpointTypes.POST_ITEM.value,
    #     )
    #     # Add the endpoint to the app
    #     self._add_endpoint_to_app(SampleEndpoint, endpoint_name, endpoint_url)
    #     # Make a request to the frontend automation endpoint
    #     response = self.client.get(
    #         self.endpoint, headers=self.get_header_with_auth(self.token)
    #     )
    #     # Check that the response is correct
    #     self.assertEqual(response.status_code, 200)
    #     self.assertIsInstance(response.json, dict)
    #     for key in ["paths", "available_automations"]:
    #         self.assertIn(key, response.json)
    #     for key in ["tables", "groups"]:
    #         self.assertIn(key, response.json["available_automations"])
    #     # Check tables
    #     self.assertIn(
    #         test_model_class.__tablename__,
    #         response.json["available_automations"]["tables"],
    #     )
    #     self.assertDictEqual(
    #         response.json["available_automations"]["tables"][
    #             test_model_class.__tablename__
    #         ],
    #         {
    #             "post_item": {"http_method": "POST", "url": endpoint_url},
    #             "group": None,
    #             "icon": None,
    #             "title": table_name,
    #             "section": None,
    #             "order": 0,
    #             "model_table_name": table_name,
    #             "schemas": None,
    #         },
    #     )
    #     # Check paths
    #     self.assertIn(endpoint_url, response.json["paths"])
    #     self.assertIn("post", response.json["paths"][endpoint_url])
    #     self.assertIn("parameters", response.json["paths"][endpoint_url]["post"])
    #     self.assertIn("responses", response.json["paths"][endpoint_url]["post"])
    #     # Check that the parameters contain the schema fields
    #     parameters = response.json["paths"][endpoint_url]["post"]["parameters"]
    #     self.assertIsInstance(parameters, list)
    #     self.assertEqual(len(parameters), 1)
    #     parameter = parameters[0]
    #     self.assertIn("in", parameter)
    #     self.assertEqual(parameter["in"], "body")
    #     self.assertIn("schema", parameter)
    #     self.assertIn("$ref", parameter["schema"])
    #     self.assertEqual(
    #         parameter["schema"]["$ref"],
    #         "#/definitions/TestModel",
    #     )
    #     # Check that the responses contain the schema fields
    #     responses = response.json["paths"][endpoint_url]["post"]["responses"]
    #     self.assertIsInstance(responses, dict)
    #     self.assertIn("default", responses)
    #     response_200 = responses["default"]
    #     self.assertIn("schema", response_200)
    #     self.assertIn("$ref", response_200["schema"])
    #     self.assertEqual(
    #         response_200["schema"]["$ref"],
    #         "#/definitions/TestModel",
    #     )
    #     # Check that the schema is in the definitions
    #     self.assertIn("definitions", response.json)
    #     self.assertIn("TestModel", response.json["definitions"])
    #     schema = response.json["definitions"]["TestModel"]
    #     self.assertDictEqual(schema, TEST_MODEL_JSONSCHEMA)
    #
    # def test_missing_schema(self):
    #     """
    #     Test the automate_frontend decorator without the required schemas arguments
    #     """
    #     endpoint_name, endpoint_url, table_name = self._get_table_endpoint_infos(6)
    #
    #     test_model_class = self._get_model_class(table_name)
    #
    #     # Post method without schema_request
    #     class SampleEndpoint(BaseMetaResource):
    #         ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES
    #
    #         def __init(sf):
    #             super().__init__()
    #             sf.data_model = test_model_class
    #
    #         @automate_frontend(
    #             EndpointTypes.POST_ITEM,
    #         )
    #         def post(self, *args, **kwargs):
    #             return {"error": "Not implemented"}, 400
    #
    #     # Check that the endpoint works correctly
    #     se = SampleEndpoint()
    #     with self.app.test_request_context(
    #         "/external" + endpoint_url,
    #         method="POST",
    #         json={"name": "Test Name", "description": "Test Description"},
    #     ):
    #         result = se.post().json
    #     self.assertIsInstance(result, dict)
    #     self.assertIn("error", result)
    #     self.assertEqual(result["error"], "Not implemented")
    #     # Check if the function doesn't have the attribute set by the decorator
    #     self.assertFalse(hasattr(se.post, "__automate_frontend__"))
    #     # Add the endpoint to the app
    #     self._add_endpoint_to_app(SampleEndpoint, endpoint_name, endpoint_url)
    #     # Make a request to the frontend automation endpoint
    #     response = self.client.get(
    #         self.endpoint, headers=self.get_header_with_auth(self.token)
    #     )
    #     # Check that the response is correct
    #     self.assertEqual(response.status_code, 200)
    #     self.assertIsInstance(response.json, dict)
    #     for key in ["paths", "available_automations"]:
    #         self.assertIn(key, response.json)
    #     for key in ["tables", "groups"]:
    #         self.assertIn(key, response.json["available_automations"])
    #     # Check that the endpoint was not added due to missing schema
    #     self.assertNotIn(
    #         test_model_class.__tablename__,
    #         response.json["available_automations"]["tables"],
    #     )
    #     self.assertNotIn(endpoint_url, response.json["paths"])
    #
    # def test_frontend_table(self):
    #     """
    #     Test the automate_frontend decorator with frontend_table argument, but without
    #     associated frontend_group
    #     """
    #     endpoint_name, endpoint_url, table_name = self._get_table_endpoint_infos(7)
    #
    #     test_model_class = self._get_model_class(table_name, FrontendTableWithoutGroup)
    #
    #     class SampleEndpoint(BaseMetaResource):
    #         ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES
    #
    #         def __init__(sf):
    #             super().__init__()
    #             sf.data_model = test_model_class
    #
    #         @automate_frontend(EndpointTypes.DELETE_ITEM)
    #         def delete(self):
    #             return {"message": "Item deleted correctly"}
    #
    #     se = SampleEndpoint()
    #     # Check that the endpoint works correctly
    #     result = se.delete().json
    #     self.assertIsInstance(result, dict)
    #     self.assertIn("message", result)
    #     self.assertEqual(result["message"], "Item deleted correctly")
    #     # Check if the function has the attribute set by the decorator
    #     self.assertTrue(hasattr(se.delete, "__automate_frontend__"))
    #     self.assertEqual(
    #         se.delete.__automate_frontend__["endpoint_type"],
    #         EndpointTypes.DELETE_ITEM.value,
    #     )
    #     # Add the endpoint to the app
    #     self._add_endpoint_to_app(SampleEndpoint, endpoint_name, endpoint_url)
    #     # Make a request to the frontend automation endpoint
    #     response = self.client.get(
    #         self.endpoint, headers=self.get_header_with_auth(self.token)
    #     )
    #     # Check that the response is correct
    #     self.assertEqual(response.status_code, 200)
    #     self.assertIsInstance(response.json, dict)
    #     for key in ["paths", "available_automations"]:
    #         self.assertIn(key, response.json)
    #     for key in ["tables", "groups"]:
    #         self.assertIn(key, response.json["available_automations"])
    #     # Check tables
    #     self.assertIn(
    #         test_model_class.__tablename__,
    #         response.json["available_automations"]["tables"],
    #     )
    #     self.assertDictEqual(
    #         response.json["available_automations"]["tables"][
    #             test_model_class.__tablename__
    #         ],
    #         {
    #             "delete_item": {"http_method": "DELETE", "url": endpoint_url},
    #             "group": None,
    #             "icon": FrontendTableWithoutGroup.icon,
    #             "title": FrontendTableWithoutGroup.title,
    #             "section": None,
    #             "order": FrontendTableWithoutGroup.order,
    #             "model_table_name": table_name,
    #             "schemas": None,
    #         },
    #     )
    #
    # def test_frontend_group(self):
    #     """
    #     Test the automate_frontend decorator with frontend_table argument and with
    #     associated frontend_group
    #     """
    #     endpoint_name, endpoint_url, table_name = self._get_table_endpoint_infos(8)
    #
    #     test_model_class = self._get_model_class(table_name, FrontendTableWithGroup)
    #
    #     class SampleEndpoint(BaseMetaResource):
    #         ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES
    #
    #         def __init__(sf):
    #             super().__init__()
    #             sf.data_model = test_model_class
    #
    #         @automate_frontend(EndpointTypes.DELETE_ITEM)
    #         def delete(self):
    #             return {"message": "Item deleted correctly"}
    #
    #     se = SampleEndpoint()
    #     # Check that the endpoint works correctly
    #     result = se.delete().json
    #     self.assertIsInstance(result, dict)
    #     self.assertIn("message", result)
    #     self.assertEqual(result["message"], "Item deleted correctly")
    #     # Check if the function has the attribute set by the decorator
    #     self.assertTrue(hasattr(se.delete, "__automate_frontend__"))
    #     self.assertEqual(
    #         se.delete.__automate_frontend__["endpoint_type"],
    #         EndpointTypes.DELETE_ITEM.value,
    #     )
    #     # Add the endpoint to the app
    #     self._add_endpoint_to_app(SampleEndpoint, endpoint_name, endpoint_url)
    #     # Make a request to the frontend automation endpoint
    #     response = self.client.get(
    #         self.endpoint, headers=self.get_header_with_auth(self.token)
    #     )
    #     # Check that the response is correct
    #     self.assertEqual(response.status_code, 200)
    #     self.assertIsInstance(response.json, dict)
    #     for key in ["paths", "available_automations"]:
    #         self.assertIn(key, response.json)
    #     for key in ["tables", "groups"]:
    #         self.assertIn(key, response.json["available_automations"])
    #     # Check tables
    #     self.assertIn(
    #         test_model_class.__tablename__,
    #         response.json["available_automations"]["tables"],
    #     )
    #     self.assertDictEqual(
    #         response.json["available_automations"]["tables"][
    #             test_model_class.__tablename__
    #         ],
    #         {
    #             "delete_item": {"http_method": "DELETE", "url": endpoint_url},
    #             "group": FrontendTableWithGroup.frontend_group.name,
    #             "icon": FrontendTableWithGroup.icon,
    #             "title": FrontendTableWithGroup.title,
    #             "section": None,
    #             "order": FrontendTableWithGroup.order,
    #             "model_table_name": table_name,
    #             "schemas": None,
    #         },
    #     )
    #     # Check groups
    #     self.assertIn(
    #         FrontendTableWithGroup.frontend_group.name,
    #         response.json["available_automations"]["groups"],
    #     )
    #     self.assertDictEqual(
    #         response.json["available_automations"]["groups"][
    #             FrontendTableWithGroup.frontend_group.name
    #         ],
    #         {
    #             "title": FrontendTableWithGroup.frontend_group.title,
    #             "icon": FrontendTableWithGroup.frontend_group.icon,
    #             "section": None,
    #             "order": FrontendTableWithGroup.frontend_group.order,
    #         },
    #     )
    #
    # def test_frontend_section(self):
    #     """
    #     Test the automate_frontend decorator with frontend_table argument and with
    #     associated frontend_section
    #     """
    #     endpoint_name, endpoint_url, table_name = self._get_table_endpoint_infos(9)
    #
    #     test_model_class = self._get_model_class(table_name, FrontendTableWithSection)
    #
    #     class SampleEndpoint(BaseMetaResource):
    #         ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES
    #
    #         def __init__(sf):
    #             super().__init__()
    #             sf.data_model = test_model_class
    #
    #         @automate_frontend(EndpointTypes.DELETE_ITEM)
    #         def delete(self):
    #             return {"message": "Item deleted correctly"}
    #
    #     se = SampleEndpoint()
    #     # Check that the endpoint works correctly
    #     result = se.delete().json
    #     self.assertIsInstance(result, dict)
    #     self.assertIn("message", result)
    #     self.assertEqual(result["message"], "Item deleted correctly")
    #     # Check if the function has the attribute set by the decorator
    #     self.assertTrue(hasattr(se.delete, "__automate_frontend__"))
    #     self.assertEqual(
    #         se.delete.__automate_frontend__["endpoint_type"],
    #         EndpointTypes.DELETE_ITEM.value,
    #     )
    #     # Add the endpoint to the app
    #     self._add_endpoint_to_app(SampleEndpoint, endpoint_name, endpoint_url)
    #     # Make a request to the frontend automation endpoint
    #     response = self.client.get(
    #         self.endpoint, headers=self.get_header_with_auth(self.token)
    #     )
    #     # Check that the response is correct
    #     self.assertEqual(response.status_code, 200)
    #     self.assertIsInstance(response.json, dict)
    #     for key in ["paths", "available_automations"]:
    #         self.assertIn(key, response.json)
    #     for key in ["tables", "groups"]:
    #         self.assertIn(key, response.json["available_automations"])
    #     # Check tables
    #     self.assertIn(
    #         test_model_class.__tablename__,
    #         response.json["available_automations"]["tables"],
    #     )
    #     self.assertDictEqual(
    #         response.json["available_automations"]["tables"][
    #             test_model_class.__tablename__
    #         ],
    #         {
    #             "delete_item": {"http_method": "DELETE", "url": endpoint_url},
    #             "group": None,
    #             "icon": FrontendTableWithSection.icon,
    #             "title": FrontendTableWithSection.title,
    #             "section": FrontendTableWithSection.frontend_section.name,
    #             "order": FrontendTableWithSection.order,
    #             "model_table_name": table_name,
    #             "schemas": None,
    #         },
    #     )
    #
    #     # Check sections
    #     self.assertIn(
    #         FrontendTableWithSection.frontend_section.name,
    #         response.json["available_automations"]["sections"],
    #     )
    #     self.assertDictEqual(
    #         response.json["available_automations"]["sections"][
    #             FrontendTableWithSection.frontend_section.name
    #         ],
    #         {
    #             "title": FrontendTableWithSection.frontend_section.title,
    #             "icon": FrontendTableWithSection.frontend_section.icon,
    #             "order": FrontendTableWithSection.frontend_section.order,
    #         },
    #     )
    #
    # def test_frontend_group_and_section(self):
    #     """
    #     Test the automate_frontend decorator with frontend_table argument and with
    #     associated frontend_group and frontend_section
    #     """
    #     endpoint_name, endpoint_url, table_name = self._get_table_endpoint_infos(10)
    #
    #     test_model_class = self._get_model_class(
    #         table_name, FrontendTableWithGroupAndSection
    #     )
    #
    #     class SampleEndpoint(BaseMetaResource):
    #         ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES
    #
    #         def __init__(sf):
    #             super().__init__()
    #             sf.data_model = test_model_class
    #
    #         @automate_frontend(EndpointTypes.DELETE_ITEM)
    #         def delete(self):
    #             return {"message": "Item deleted correctly"}
    #
    #     se = SampleEndpoint()
    #     # Check that the endpoint works correctly
    #     result = se.delete().json
    #     self.assertIsInstance(result, dict)
    #     self.assertIn("message", result)
    #     self.assertEqual(result["message"], "Item deleted correctly")
    #     # Check if the function has the attribute set by the decorator
    #     self.assertTrue(hasattr(se.delete, "__automate_frontend__"))
    #     self.assertEqual(
    #         se.delete.__automate_frontend__["endpoint_type"],
    #         EndpointTypes.DELETE_ITEM.value,
    #     )
    #     # Add the endpoint to the app
    #     self._add_endpoint_to_app(SampleEndpoint, endpoint_name, endpoint_url)
    #     # Make a request to the frontend automation endpoint
    #     response = self.client.get(
    #         self.endpoint, headers=self.get_header_with_auth(self.token)
    #     )
    #     # Check that the response is correct
    #     self.assertEqual(response.status_code, 200)
    #     self.assertIsInstance(response.json, dict)
    #     for key in ["paths", "available_automations"]:
    #         self.assertIn(key, response.json)
    #     for key in ["tables", "groups"]:
    #         self.assertIn(key, response.json["available_automations"])
    #     # Check tables
    #     self.assertIn(
    #         test_model_class.__tablename__,
    #         response.json["available_automations"]["tables"],
    #     )
    #     self.assertDictEqual(
    #         response.json["available_automations"]["tables"][
    #             test_model_class.__tablename__
    #         ],
    #         {
    #             "delete_item": {"http_method": "DELETE", "url": endpoint_url},
    #             "group": FrontendTableWithGroupAndSection.frontend_group.name,
    #             "icon": FrontendTableWithGroupAndSection.icon,
    #             "title": FrontendTableWithGroupAndSection.title,
    #             "section": None,
    #             "order": FrontendTableWithGroupAndSection.order,
    #             "model_table_name": table_name,
    #             "schemas": None,
    #         },
    #     )
    #
    #     # Check groups
    #     self.assertIn(
    #         FrontendTableWithGroupAndSection.frontend_group.name,
    #         response.json["available_automations"]["groups"],
    #     )
    #     self.assertDictEqual(
    #         response.json["available_automations"]["groups"][
    #             FrontendTableWithGroupAndSection.frontend_group.name
    #         ],
    #         {
    #             "title": FrontendTableWithGroupAndSection.frontend_group.title,
    #             "icon": FrontendTableWithGroupAndSection.frontend_group.icon,
    #             "section": FrontendTableWithGroupAndSection.frontend_group.frontend_section.name,
    #             "order": FrontendTableWithGroupAndSection.frontend_group.order,
    #         },
    #     )
    #
    #     # Check sections
    #     self.assertIn(
    #         FrontendTableWithGroupAndSection.frontend_group.frontend_section.name,
    #         response.json["available_automations"]["sections"],
    #     )
    #     self.assertDictEqual(
    #         response.json["available_automations"]["sections"][
    #             FrontendTableWithGroupAndSection.frontend_group.frontend_section.name
    #         ],
    #         {
    #             "title": FrontendTableWithGroupAndSection.frontend_group.frontend_section.title,
    #             "icon": FrontendTableWithGroupAndSection.frontend_group.frontend_section.icon,
    #             "order": FrontendTableWithGroupAndSection.frontend_group.frontend_section.order,
    #         },
    #     )

    def _register_simple_endpoint(self, index, frontend_table=None):
        """
        Helper to register a simple DELETE endpoint with a given frontend_table.
        Returns (endpoint_url, table_name).
        """
        endpoint_name, endpoint_url, table_name = self._get_table_endpoint_infos(index)
        test_model_class = self._get_model_class(table_name, frontend_table)

        class _Endpoint(BaseMetaResource):
            ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES

            def __init__(sf):
                super().__init__()
                sf.data_model = test_model_class

            @automate_frontend(EndpointTypes.DELETE_ITEM)
            def delete(self):
                return {"message": "Item deleted correctly"}

        self._add_endpoint_to_app(_Endpoint, endpoint_name, endpoint_url)
        return endpoint_url, table_name

    # def test_frontend_table_with_schemas(self):
    #     """
    #     Test the automate_frontend decorator with a frontend_table that defines a
    #     non-None schemas list
    #     """
    #     endpoint_name, endpoint_url, table_name = self._get_table_endpoint_infos(11)
    #
    #     test_model_class = self._get_model_class(table_name, FrontendTableWithSchemas)
    #
    #     class SampleEndpoint(BaseMetaResource):
    #         ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES
    #
    #         def __init__(sf):
    #             super().__init__()
    #             sf.data_model = test_model_class
    #
    #         @automate_frontend(EndpointTypes.DELETE_ITEM)
    #         def delete(self):
    #             return {"message": "Item deleted correctly"}
    #
    #     se = SampleEndpoint()
    #     result = se.delete().json
    #     self.assertIsInstance(result, dict)
    #     self.assertIn("message", result)
    #     self.assertEqual(result["message"], "Item deleted correctly")
    #     self.assertTrue(hasattr(se.delete, "__automate_frontend__"))
    #     self.assertEqual(
    #         se.delete.__automate_frontend__["endpoint_type"],
    #         EndpointTypes.DELETE_ITEM.value,
    #     )
    #     self._add_endpoint_to_app(SampleEndpoint, endpoint_name, endpoint_url)
    #     response = self.client.get(
    #         self.endpoint, headers=self.get_header_with_auth(self.token)
    #     )
    #     self.assertEqual(response.status_code, 200)
    #     self.assertIsInstance(response.json, dict)
    #     for key in ["paths", "available_automations"]:
    #         self.assertIn(key, response.json)
    #     for key in ["tables", "groups"]:
    #         self.assertIn(key, response.json["available_automations"])
    #     # Check tables
    #     self.assertIn(
    #         test_model_class.__tablename__,
    #         response.json["available_automations"]["tables"],
    #     )
    #     table_data = response.json["available_automations"]["tables"][
    #         test_model_class.__tablename__
    #     ]
    #     self.assertDictEqual(
    #         table_data,
    #         {
    #             "delete_item": {"http_method": "DELETE", "url": endpoint_url},
    #             "group": None,
    #             "icon": FrontendTableWithSchemas.icon,
    #             "title": FrontendTableWithSchemas.title,
    #             "section": None,
    #             "order": FrontendTableWithSchemas.order,
    #             "model_table_name": table_name,
    #             "schemas": ["solve_model_dag", "gc"],
    #         },
    #     )
    #     # Verify schemas is not None and contains the expected values
    #     self.assertIsNotNone(table_data["schemas"])
    #     self.assertIsInstance(table_data["schemas"], list)
    #     self.assertEqual(len(table_data["schemas"]), 2)
    #     self.assertIn("solve_model_dag", table_data["schemas"])
    #     self.assertIn("gc", table_data["schemas"])
    #     # Check paths
    #     self.assertIn(endpoint_url, response.json["paths"])
    #     self.assertDictEqual(
    #         response.json["paths"][endpoint_url],
    #         {"delete": {"parameters": [], "responses": {}}},
    #     )
    #
    # # ── Schema filtering & permission tests ────────────────────────────
    #
    # def test_requested_schema_no_permission_returns_403(self):
    #     """
    #     Requesting ?schema=<dag_without_permission> should return 403.
    #     """
    #     response = self.client.get(
    #         self.endpoint + "?schema=nonexistent_dag",
    #         headers=self.get_header_with_auth(self.token),
    #     )
    #     self.assertEqual(response.status_code, 403)
    #
    # def test_requested_schema_with_permission_returns_200(self):
    #     """
    #     Requesting ?schema=<permitted_dag> should return 200.
    #     """
    #     response = self.client.get(
    #         self.endpoint + "?schema=solve_model_dag",
    #         headers=self.get_header_with_auth(self.token),
    #     )
    #     self.assertEqual(response.status_code, 200)
    #
    # def test_schema_filter_excludes_unrelated_tables(self):
    #     """
    #     When ?schema=solve_model_dag is passed, tables whose schemas list does not
    #     contain that value should be excluded, while matching ones remain.
    #     """
    #     url_dag, table_dag = self._register_simple_endpoint(
    #         12, FrontendTableWithSchemaDag
    #     )
    #     url_two, table_two = self._register_simple_endpoint(
    #         13, FrontendTableWithSchemaTwoDag
    #     )
    #
    #     response = self.client.get(
    #         self.endpoint + "?schema=solve_model_dag",
    #         headers=self.get_header_with_auth(self.token),
    #     )
    #     self.assertEqual(response.status_code, 200)
    #     tables = response.json["available_automations"]["tables"]
    #     self.assertIn(table_dag, tables)
    #     self.assertNotIn(table_two, tables)
    #
    # def test_schema_filter_keeps_tables_with_null_schemas(self):
    #     """
    #     Tables with schemas=None should always pass through the ?schema filter because
    #     they are not tied to any specific schema.
    #     """
    #     url_dag, table_dag = self._register_simple_endpoint(
    #         14, FrontendTableWithSchemaDag
    #     )
    #     url_null, table_null = self._register_simple_endpoint(15, None)
    #
    #     response = self.client.get(
    #         self.endpoint + "?schema=solve_model_dag",
    #         headers=self.get_header_with_auth(self.token),
    #     )
    #     self.assertEqual(response.status_code, 200)
    #     tables = response.json["available_automations"]["tables"]
    #     self.assertIn(table_dag, tables)
    #     self.assertIn(table_null, tables)
    #
    # def test_schema_filter_multi_schema_table(self):
    #     """
    #     A table whose schemas list contains both DAGs should be included when either
    #     one is requested.
    #     """
    #     url_both, table_both = self._register_simple_endpoint(
    #         16, FrontendTableWithSchemas
    #     )
    #
    #     for schema in ["solve_model_dag", "gc"]:
    #         response = self.client.get(
    #             self.endpoint + f"?schema={schema}",
    #             headers=self.get_header_with_auth(self.token),
    #         )
    #         self.assertEqual(response.status_code, 200)
    #         tables = response.json["available_automations"]["tables"]
    #         self.assertIn(
    #             table_both,
    #             tables,
    #             f"Table should be present when filtering by {schema}",
    #         )
    #
    # def test_no_schema_param_filters_by_user_permissions(self):
    #     """
    #     Without ?schema, tables whose schemas list only contains DAGs the user does NOT
    #     have permission for should be excluded.
    #     """
    #     url_dag, table_dag = self._register_simple_endpoint(
    #         17, FrontendTableWithSchemaDag
    #     )
    #     url_unknown, table_unknown = self._register_simple_endpoint(
    #         18, FrontendTableWithUnknownSchema
    #     )
    #
    #     response = self.client.get(
    #         self.endpoint,
    #         headers=self.get_header_with_auth(self.token),
    #     )
    #     self.assertEqual(response.status_code, 200)
    #     tables = response.json["available_automations"]["tables"]
    #     self.assertIn(table_dag, tables)
    #     self.assertNotIn(table_unknown, tables)
    #
    # def test_no_schema_param_keeps_null_schema_tables(self):
    #     """
    #     Without ?schema, tables with schemas=None bypass the permission filter and
    #     always appear.
    #     """
    #     url_null, table_null = self._register_simple_endpoint(19, None)
    #
    #     response = self.client.get(
    #         self.endpoint,
    #         headers=self.get_header_with_auth(self.token),
    #     )
    #     self.assertEqual(response.status_code, 200)
    #     tables = response.json["available_automations"]["tables"]
    #     self.assertIn(table_null, tables)
    #
    # def test_partial_permission_on_multi_schema_table(self):
    #     """
    #     A table with schemas = ["solve_model_dag", "nonexistent_dag"] should still
    #     appear because the user has permission for at least one (any() semantics).
    #     """
    #     url_mixed, table_mixed = self._register_simple_endpoint(
    #         20, FrontendTableWithMixedSchemas
    #     )
    #
    #     response = self.client.get(
    #         self.endpoint,
    #         headers=self.get_header_with_auth(self.token),
    #     )
    #     self.assertEqual(response.status_code, 200)
    #     tables = response.json["available_automations"]["tables"]
    #     self.assertIn(table_mixed, tables)

    # ── Resource discovery from plugins and external apps ───────────────

    def _build_external_resource(self, index, register_url=None):
        """
        Build a resource that is NOT part of the core resources list, so it
        can be injected through a plugin or an external app. The route, view and
        permission are registered on the app so the resource is discoverable and the
        requesting user is allowed to see it; the only thing missing is its presence in
        the core ``resources`` list.

        The route is registered at the resource's root URL, matching production: the
        external app and the cornflow app are mounted under "/external" and "/cornflow"
        via DispatcherMiddleware, which strips that prefix before the request reaches each
        app, so inside the app the rule lives at the root URL the apispec lookup is keyed
        by. The endpoint applies the "/external/" or "/cornflow/" prefix only to the
        client-facing URL it emits. ``register_url`` can still override the route URL for
        tests that need it.

        Returns ``(resource_dict, table_name)``.
        """
        endpoint_name, endpoint_url, table_name = self._get_table_endpoint_infos(
            index, is_external=True
        )
        test_model_class = self._get_model_class(table_name)

        class _ExternalEndpoint(BaseMetaResource):
            ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES

            def __init__(sf):
                super().__init__()
                sf.data_model = test_model_class

            @automate_frontend(EndpointTypes.DELETE_ITEM)
            def delete(self):
                return {"message": "Item deleted correctly"}

        route_url = register_url or endpoint_url
        resource = {
            "resource": _ExternalEndpoint,
            "urls": endpoint_url.replace("/external", ""),
            "endpoint": endpoint_name,
        }
        self._register_route(_ExternalEndpoint, endpoint_name, route_url)
        # The view is registered at the URL the route lives at, so permissions resolve
        # against the same url_rule the auth layer sees at request time.
        self._register_view_and_permission({**resource, "urls": route_url})
        return resource, table_name

    # def test_resources_automated_from_plugin(self):
    #     """
    #     Resources provided by a discovered plugin (via the ``cornflow.plugins`` entry
    #     points) should be picked up and automated.
    #     """
    #     resource, table_name = self._build_external_resource(21)
    #
    #     # The resource is not part of the core resources list, so it can only end up in
    #     # the output if the plugin discovery path picks it up.
    #     self.assertNotIn(resource, resources)
    #
    #     # Fake plugin exposing the resource through get_resources(), and a fake entry
    #     # point that loads it. The endpoint module imports entry_points directly, so we
    #     # patch it in that namespace.
    #     class _FakePlugin:
    #         def get_resources(self):
    #             return [{**resource, "urls": "/external" + resource["urls"]}]
    #
    #     fake_entry_point = types.SimpleNamespace(
    #         load=lambda: _FakePlugin, name="fake_plugin"
    #     )
    #
    #     def fake_entry_points(group=None):
    #         if group == "cornflow.plugins":
    #             return [fake_entry_point]
    #         return []
    #
    #     with patch(
    #         "cornflow.endpoints.frontend_automation.entry_points",
    #         side_effect=fake_entry_points,
    #     ):
    #         response = self.client.get(
    #             self.endpoint, headers=self.get_header_with_auth(self.token)
    #         )
    #
    #     self.assertEqual(response.status_code, 200)
    #     tables = response.json["available_automations"]["tables"]
    #     self.assertIn(table_name, tables)
    #     self.assertIn("delete_item", tables[table_name])
    #     self.assertEqual(
    #         tables[table_name]["delete_item"],
    #         {"http_method": "DELETE", "url": "/external" + resource["urls"]},
    #     )

    def test_resources_automated_from_external_app(self):
        """
        Resources provided by a configured external app (EXTERNAL_APP=1 +
        EXTERNAL_APP_MODULE) should be picked up and automated.
        """
        endpoint_url = self._get_table_endpoint_infos(22)[1]
        prefixed_url = ("/external/" + endpoint_url).replace("//", "/")
        # The route lives at its root URL inside the app (DispatcherMiddleware strips the
        # "/external" mount prefix before the request reaches the external app), so the
        # apispec lookup matches the root URL. The "/external/" prefix is applied only to
        # the client-facing URL in the output.
        resource, table_name = self._build_external_resource(22)

        # The resource is not part of the core resources list, so it can only end up in
        # the output if the external app discovery path picks it up.
        self.assertNotIn(resource, resources)

        # Hand the endpoint a fresh copy so the shared assertion dict stays clean.
        external_resource = dict(resource)

        # Fake external app module exposing endpoints.resources, returned by the patched
        # import_module in the endpoint's namespace.
        fake_external_module = types.ModuleType("fake_external_app")
        fake_external_module.endpoints = types.SimpleNamespace(
            resources=[external_resource]
        )

        original_external_app = current_app.config["EXTERNAL_APP"]
        current_app.config["EXTERNAL_APP"] = 1
        try:
            with patch.dict(
                "os.environ", {"EXTERNAL_APP_MODULE": "fake_external_app"}
            ), patch(
                "cornflow.endpoints.frontend_automation.import_module",
                return_value=fake_external_module,
            ):
                response = self.client.get(
                    self.endpoint, headers=self.get_header_with_auth(self.token)
                )
        finally:
            current_app.config["EXTERNAL_APP"] = original_external_app
        print(response.json)
        self.assertEqual(response.status_code, 200)
        tables = response.json["available_automations"]["tables"]
        self.assertIn(table_name, tables)
        self.assertIn("delete_item", tables[table_name])
        # The automated URL should be the /external/-prefixed one.
        self.assertEqual(
            tables[table_name]["delete_item"],
            {"http_method": "DELETE", "url": "/external" + resource["urls"]},
        )
        # The "paths" block is rewritten to the same prefixed URL.
        self.assertIn(prefixed_url, response.json["paths"])
        self.assertNotIn(endpoint_url, response.json["paths"])
