"""
External endpoints to manage the cases: create new cases from raw data, from an existing instance or execution
or from an existing case, update the case info, patch its data, get all of them or one, move them and delete them.
These endpoints have different access url, but manage the same data entities
"""
# Import from libraries
from cornflow_client.constants import (
    INSTANCE_SCHEMA,
    SOLUTION_SCHEMA
)
from flask import current_app
from flask_apispec import marshal_with, use_kwargs, doc
from flask_inflate import inflate
import jsonpatch


# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import CaseModel, ExecutionModel, DeployedDAG, InstanceModel
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.compress import compressed
from cornflow.shared.const import VIEWER_ROLE, PLANNER_ROLE, ADMIN_ROLE
from cornflow.shared.exceptions import InvalidData, ObjectDoesNotExist
from cornflow.shared.validators import json_schema_validate_as_string
from cornflow.schemas.case import (
    CaseBase,
    CaseFromInstanceExecution,
    CaseRawRequest,
    CaseListResponse,
    CaseToInstanceResponse,
    CaseEditRequest,
    QueryFiltersCase,
    QueryCaseCompare,
    CaseCompareResponse,
    CaseListAllWithIndicators,
)


class CaseEndpoint(BaseMetaResource):
    """
    Endpoint used to create a new case or get all the cases and their related information
    """
    ROLES_WITH_ACCESS = [VIEWER_ROLE, PLANNER_ROLE, ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = CaseModel

    @doc(description="Get all cases", tags=["Cases"])
    @authenticate(auth_class=Auth())
    @marshal_with(CaseListAllWithIndicators(many=True))
    @use_kwargs(QueryFiltersCase, location="query")
    def get(self, **kwargs):
        """
        API (GET) method to get all directory structure of cases for the user
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: a dictionary with a tree structure of the cases and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """

        response = self.get_list(user=self.get_user(), **kwargs)
        current_app.logger.info(f"User {self.get_user()} gets all cases")
        return response

    @doc(description="Create a new case from raw data", tags=["Cases"])
    @authenticate(auth_class=Auth())
    @Auth.dag_permission_required
    @inflate
    @marshal_with(CaseListResponse)
    @use_kwargs(CaseRawRequest, location="json")
    def post(self, **kwargs):
        """ """
        data = dict(kwargs)
        data["user_id"] = self.get_user_id()
        schema = data["schema"]
        config = current_app.config

        # We validate the instance data if it exists
        if kwargs.get("data") is not None:
            data_schema = DeployedDAG.get_one_schema(config, schema, INSTANCE_SCHEMA)
            data_errors = json_schema_validate_as_string(data_schema, kwargs["data"])
            if data_errors:
                raise InvalidData(payload=dict(jsonschema_errors=data_errors))

        # And the solution data if it exists
        if kwargs.get("solution") is not None:
            solution_schema = DeployedDAG.get_one_schema(config, schema, SOLUTION_SCHEMA)
            solution_errors = json_schema_validate_as_string(solution_schema, kwargs["solution"])
            if solution_errors:
                raise InvalidData(payload=dict(jsonschema_errors=solution_errors))

        # And if everything is okay: we create the case
        item = CaseModel.from_parent_id(self.get_user(), data)
        item.save()
        current_app.logger.info(f"User {self.get_user()} creates case {item.id}")
        return item, 201


class CaseFromInstanceExecutionEndpoint(BaseMetaResource):
    """
    Endpoint used to create a new case from an already existing instance and execution
    """
    ROLES_WITH_ACCESS = [PLANNER_ROLE, ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = CaseModel

    @doc(description="Create a new case from instance and execution", tags=["Cases"])
    @authenticate(auth_class=Auth())
    @Auth.dag_permission_required
    @marshal_with(CaseListResponse)
    @use_kwargs(CaseFromInstanceExecution, location="json")
    def post(self, **kwargs):
        """
        API method to create a new case from an existing instance or execution
        """
        instance_id = kwargs.get("instance_id", None)
        execution_id = kwargs.get("execution_id", None)

        data = {name: kwargs.get(name) for name in ["name", "description", "parent_id"]}

        if (instance_id is not None and execution_id is not None) or (
            instance_id is None and execution_id is None
        ):
            raise InvalidData(
                error="You must provide a valid instance_id OR an execution_id",
                status_code=400,
                log_txt=f"Error while user {self.get_user()} tries to create case from instance and execution. "
                        f"The instance id or execution id is not valid."
            )
        user = self.get_user()

        def get_instance_data(instance_id):
            instance = InstanceModel.get_one_object(user=user, idx=instance_id)
            if instance is None:
                err = "Instance does not exist."
                raise ObjectDoesNotExist(
                    err,
                    log_txt=f"Error while user {self.get_user()} tries to create case "
                            f"from instance and execution. " + err
                )
            return dict(
                data=instance.data, schema=instance.schema, checks=instance.checks
            )

        def get_execution_data(execution_id):
            execution = ExecutionModel.get_one_object(user=user, idx=execution_id)
            if execution is None:
                err = "Execution does not exist."
                raise ObjectDoesNotExist(
                    err,
                    log_txt=f"Error while user {self.get_user()} tries to create "
                            f"case from instance and execution. " + err
                )
            data = get_instance_data(execution.instance_id)
            data["solution"] = execution.data
            data["solution_checks"] = execution.checks
            return data

        if instance_id is not None:
            data = {**data, **get_instance_data(instance_id)}
        elif execution_id is not None:
            data = {**data, **get_execution_data(execution_id)}

        data = dict(data)
        data["user_id"] = self.get_user_id()
        item = CaseModel.from_parent_id(user, data)
        item.save()
        current_app.logger.info(
            f"User {self.get_user()} creates case {item.id} from instance/execution."
        )
        return item, 201


class CaseCopyEndpoint(BaseMetaResource):
    """
    Copies the case to a new case. Original case id goes in the url
    """
    ROLES_WITH_ACCESS = [PLANNER_ROLE, ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.model = CaseModel
        self.data_model = CaseModel
        self.query = self.model.get_all_objects
        self.primary_key = "id"
        self.fields_to_copy = [
            "name",
            "description",
            "data",
            "checks",
            "schema",
            "solution",
            "solution_checks",
            "path",
        ]
        self.fields_to_modify = ["name"]

    @doc(description="Copies a case to a new one", tags=["Cases"])
    @authenticate(auth_class=Auth())
    @marshal_with(CaseListResponse)
    def post(self, idx):
        """ """
        case = self.model.get_one_object(user=self.get_user(), idx=idx)
        data = case.__dict__
        payload = dict()
        for key in data.keys():
            if key in self.fields_to_copy:
                payload[key] = data[key]
            if key in self.fields_to_modify:
                payload[key] = "Copy_" + data[key]

        response = self.post_list(payload)
        current_app.logger.info(f"User {self.get_user()} copied case {idx} into {response[0].id}")
        return response


class CaseDetailsEndpoint(BaseMetaResource):
    """
    Endpoint used to get the information of a single case, edit it or delete it
    """
    ROLES_WITH_ACCESS = [VIEWER_ROLE, PLANNER_ROLE, ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = CaseModel

    @doc(description="Get one case", tags=["Cases"], inherit=False)
    @authenticate(auth_class=Auth())
    @marshal_with(CaseListAllWithIndicators)
    @BaseMetaResource.get_data_or_404
    def get(self, idx):
        """
        API method to get an case created by the user and its related info.

        :param str idx: ID of the case
        :return: A dictionary with a message and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        response = self.get_detail(idx=idx, user=self.get_user())
        current_app.logger.info(f"User {self.get_user()} gets case {idx}")
        return response

    @doc(description="Edit a case", tags=["Cases"])
    @authenticate(auth_class=Auth())
    @use_kwargs(CaseEditRequest, location="json")
    def put(self, idx, **kwargs):
        """
        API method to edit a case created by the user and its basic related info (name, description and schema).

        :param int idx: ID of the case
        :return: A dictionary with a confirmation message and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        current_app.logger.info(f"User {self.get_user()} edits case {idx}")
        if kwargs.get("parent_id", 0) != 0:
            parent_id = kwargs.pop("parent_id")
            case = self.data_model.get_one_object(idx=idx, user=self.get_user())
            parent_case = None
            if case is None:
                err = "The data entity does not exist on the database."
                raise ObjectDoesNotExist(
                    err,
                    log_txt=f"Error while user {self.get_user()} tries to edit case {idx}. " + err
                )
            if parent_id is not None:
                parent_case = self.data_model.get_one_object(
                    idx=parent_id, user=self.get_user()
                )
                if case is None or parent_case is None:
                    err = "The data entity does not exist on the database."
                    raise ObjectDoesNotExist(
                        err,
                        log_txt=f"Error while user {self.get_user()} tries to move "
                                f"case {idx} to directory {idx}. " + err
                    )

            case.move_to(parent_case)

        return self.put_detail(data=kwargs, idx=idx, user=self.get_user())

    @doc(description="Delete a case", tags=["Cases"])
    @authenticate(auth_class=Auth())
    def delete(self, idx):
        """
        API method to delete an existing case.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param int idx: ID of the case
        :return: A dictionary with a confirmation message and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        current_app.logger.info(f"User {self.get_user()} deletes case {idx}")
        return self.delete_detail(idx=idx, user=self.get_user())


class CaseDataEndpoint(CaseDetailsEndpoint):
    """
    Endpoint used to get the data of a given case
    """
    ROLES_WITH_ACCESS = [VIEWER_ROLE, PLANNER_ROLE, ADMIN_ROLE]

    @doc(description="Get data of a case", tags=["Cases"], inherit=False)
    @authenticate(auth_class=Auth())
    @marshal_with(CaseBase)
    @BaseMetaResource.get_data_or_404
    @compressed
    def get(self, idx):
        """
        API method to get data for a case by the user and its related info.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param int idx: ID of the case
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the instance) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        response = self.get_detail(idx=idx, user=self.get_user())
        current_app.logger.info(f"User {self.get_user()} gets case {idx}")
        return response

    @doc(description="Patches the data of a given case", tags=["Cases"], inherit=False)
    @authenticate(auth_class=Auth())
    @inflate
    @use_kwargs(CaseCompareResponse, location="json")
    def patch(self, idx, **kwargs):
        response = self.patch_detail(data=kwargs, idx=idx, user=self.get_user())
        current_app.logger.info(f"User {self.get_user()} patches case {idx}")
        return response


class CaseToInstance(BaseMetaResource):
    """
    Endpoint used to create a new instance or instance and execution from a stored case
    """
    ROLES_WITH_ACCESS = [PLANNER_ROLE, ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = InstanceModel

    @doc(
        description="Copies the information stored in a case into a new instance",
        tags=["Cases"],
    )
    @authenticate(auth_class=Auth())
    @marshal_with(CaseToInstanceResponse)
    def post(self, idx):
        """
        API method to copy the information stored in a case to a new instance
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :param int idx: ID of the case that has to be copied to an instance or instance and execution
        :return: an object with the instance or instance and execution ID that have been created and the status code
        :rtype: Tuple (dict, integer)
        """
        case = CaseModel.get_one_object(user=self.get_user(), idx=idx)

        if case is None:
            raise ObjectDoesNotExist()

        schema = case.schema
        payload = {
            "name": "instance_from_" + case.name,
            "description": "Instance created from " + case.description,
            "data": case.data,
            "schema": case.schema,
        }

        if schema is None:
            return self.post_list(payload)

        if schema == "pulp":
            # The dag name is solve_model_dag
            schema = "solve_model_dag"

        config = current_app.config

        # Data validation
        jsonschema = DeployedDAG.get_one_schema(config, schema, INSTANCE_SCHEMA)
        data_errors = json_schema_validate_as_string(jsonschema, payload["data"])
        if data_errors:
            raise InvalidData(
                payload=dict(jsonschema_errors=data_errors),
                log_txt=f"Error while user {self.get_user()} tries to create instance from case {idx}. "
                        f"Data do not match the jsonschema.",
            )

        response = self.post_list(payload)
        current_app.logger.info(
            f"User {self.get_user()} creates instance {response[0].id} from case {idx}."
        )
        return response


class CaseCompare(BaseMetaResource):
    """
    Endpoint used to generate the json patch of two given cases
    """
    ROLES_WITH_ACCESS = [VIEWER_ROLE, PLANNER_ROLE, ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.model = CaseModel
        self.query = CaseModel.get_all_objects
        self.primary_key = "id"

    @doc(
        description="Compares the data and / or solution of two given cases",
        tags=["Cases"],
    )
    @authenticate(auth_class=Auth())
    @marshal_with(CaseCompareResponse)
    @use_kwargs(QueryCaseCompare, location="query")
    @compressed
    def get(self, idx1, idx2, **kwargs):
        """
        API method to generate the json patch of two cases given by the user
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :param int idx1: ID of the base case for the comparison
        :param int idx2: ID of the case that has to be compared
        :return:an object with the instance or instance and execution ID that have been created and the status code
        :rtype: Tuple (dict, integer)
        """
        if idx1 == idx2:
            raise InvalidData(
                "The case identifiers should be different.",
                400,
                log_txt=f"Error while user {self.get_user()} tries to compare cases. "
                        f"The cases to compare have the same identifier."
            )
        case_1 = self.model.get_one_object(user=self.get_user(), idx=idx1)
        case_2 = self.model.get_one_object(user=self.get_user(), idx=idx2)

        if case_1 is None:
            raise ObjectDoesNotExist(
                "You don't have access to the first case or it doesn't exist",
                log_txt=f"Error while user {self.get_user()} tries to compare cases {idx1} and {idx2}. "
                        f"The user doesn't have access to case {idx1} or it does not exist."
            )
        elif case_2 is None:
            raise ObjectDoesNotExist(
                "You don't have access to the second case or it doesn't exist",
                log_txt=f"Error while user {self.get_user()} tries to compare cases {idx1} and {idx2}. "
                        f"The user doesn't have access to case {idx2} or it does not exist."
            )
        elif case_1.schema != case_2.schema:
            raise InvalidData(
                "The cases asked to compare do not share the same schema",
                log_txt=f"Error while user {self.get_user()} tries to compare cases {idx1} and {idx2}. "
                        f"The cases don't have the same schemas."
            )

        data = kwargs.get("data", True)
        solution = kwargs.get("solution", True)
        payload = dict()

        if data:
            payload["data_patch"] = jsonpatch.make_patch(case_1.data, case_2.data).patch
        if solution:
            payload["solution_patch"] = jsonpatch.make_patch(
                case_1.solution, case_2.solution
            ).patch

        payload["schema"] = case_1.schema
        current_app.logger.info(f"User {self.get_user()} compared cases {idx1} and {idx2}")
        return payload, 200
