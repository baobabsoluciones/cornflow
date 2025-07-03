"""
External endpoints to launch the solution check on an execution
"""

# Import from libraries
from cornflow_client.airflow.api import Airflow
from cornflow_client.constants import INSTANCE_SCHEMA, SOLUTION_SCHEMA
from flask import request, current_app
from flask_apispec import marshal_with, doc

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import InstanceModel, ExecutionModel, CaseModel, DeployedDAG
from cornflow.schemas.execution import ExecutionDetailsEndpointResponse
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import (
    AIRFLOW_ERROR_MSG,
    AIRFLOW_NOT_REACHABLE_MSG,
    DAG_PAUSED_MSG,
    EXEC_STATE_QUEUED,
    EXEC_STATE_ERROR,
    EXEC_STATE_ERROR_START,
    EXEC_STATE_NOT_RUN,
    EXECUTION_STATE_MESSAGE_DICT,
    PLANNER_ROLE,
    ADMIN_ROLE,
)
from cornflow.shared.exceptions import (
    AirflowError,
    ObjectDoesNotExist,
    InvalidUsage,
    InvalidData,
)
from cornflow.shared.validators import json_schema_validate_as_string


def _run_airflow_data_check(
    af_client: Airflow,
    execution: ExecutionModel,
    schema: str,
    user,
    context_str: str,
    **run_dag_kwargs,
):
    """
    Helper function to check Airflow status and run a data check DAG.

    :param af_client: Initialized Airflow client.
    :param execution: The ExecutionModel object to update.
    :param schema: The name of the schema/DAG to run.
    :param user: The user object performing the action.
    :param context_str: A string describing the context (e.g., "execution {id}") for logging.
    :param run_dag_kwargs: Additional keyword arguments for af_client.run_dag.
    :return: None. Updates execution object in place and raises AirflowError on failure.
    """
    # Check Airflow liveness
    if not af_client.is_alive():
        current_app.logger.error(AIRFLOW_NOT_REACHABLE_MSG)
        execution.update_state(EXEC_STATE_ERROR_START)
        raise AirflowError(
            error=AIRFLOW_NOT_REACHABLE_MSG,
            payload=dict(
                message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                state=EXEC_STATE_ERROR_START,
            ),
            log_txt=f"Error while user {user} tries to run data checks on {context_str}. "
            + AIRFLOW_NOT_REACHABLE_MSG,
        )

    # Check if DAG is paused
    schema_info = af_client.get_dag_info(schema)
    info = schema_info.json()
    if info.get("is_paused", False):
        current_app.logger.error(DAG_PAUSED_MSG)
        execution.update_state(EXEC_STATE_ERROR_START)
        raise AirflowError(
            error=DAG_PAUSED_MSG,
            payload=dict(
                message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                state=EXEC_STATE_ERROR_START,
            ),
            log_txt=f"Error while user {user} tries to run data checks on {context_str}. "
            + DAG_PAUSED_MSG,
        )

    # Run the DAG
    try:
        response = af_client.run_dag(
            execution.id, dag_name=schema, checks_only=True, **run_dag_kwargs
        )
    except AirflowError as err:
        error = f"{AIRFLOW_ERROR_MSG} {err}"
        current_app.logger.error(error)
        execution.update_state(EXEC_STATE_ERROR)
        raise AirflowError(
            error=error,
            payload=dict(
                message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                state=EXEC_STATE_ERROR,
            ),
            log_txt=f"Error while user {user} tries to run data checks on {context_str}. "
            + error,
        )

    # Update execution on success
    af_data = response.json()
    execution.dag_run_id = af_data.get("dag_run_id")
    execution.update_state(EXEC_STATE_QUEUED)


class DataCheckExecutionEndpoint(BaseMetaResource):
    """
    Endpoint used to execute the instance and solution checks on an execution
    """

    ROLES_WITH_ACCESS = [PLANNER_ROLE, ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.model = ExecutionModel
        self.data_model = ExecutionModel
        self.foreign_data = {"instance_id": InstanceModel}

    @doc(description="Create a data check execution", tags=["Data checks"])
    @authenticate(auth_class=Auth())
    @Auth.dag_permission_required
    @marshal_with(ExecutionDetailsEndpointResponse)
    def post(self, idx):
        """
        API method to execute only the checks of an existing execution
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed, error if data is not validated or
          the reference_id for the newly created execution if successful) and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        config = current_app.config
        user = self.get_user()
        context_str = f"execution {idx}"

        execution = ExecutionModel.get_one_object(user=self.get_user(), idx=idx)
        if execution is None:
            err = "The execution to check does not exist"
            raise ObjectDoesNotExist(
                error=err,
                log_txt=f"Error while user {user} tries to run data checks on {context_str}. "
                + err,
            )

        schema = execution.schema

        # If the execution is still running or queued, raise an error
        if execution.state == 0 or execution.state == -7:
            err = "The execution is still running"
            raise InvalidUsage(
                error=err,
                log_txt=f"Error while user {user} tries to run data checks on {context_str}. "
                + err,
            )

        # this allows testing without airflow interaction:
        if request.args.get("run", "1") == "0":
            execution.update_state(EXEC_STATE_NOT_RUN)
            return execution, 201

        # Initialize Airflow client
        af_client = Airflow.from_config(config)

        # Call the shared Airflow execution logic
        _run_airflow_data_check(af_client, execution, schema, user, context_str)

        current_app.logger.info(
            "User {} launches checks of execution {}".format(
                self.get_user_id(), execution.id
            )
        )
        return execution, 201


class DataCheckInstanceEndpoint(BaseMetaResource):
    """
    Endpoint used to execute the instance and solution checks on an execution
    """

    ROLES_WITH_ACCESS = [PLANNER_ROLE, ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.model = ExecutionModel
        self.data_model = ExecutionModel
        self.foreign_data = {"instance_id": InstanceModel}

    @doc(
        description="Create a data check execution for an existing instance",
        tags=["Data checks"],
    )
    @authenticate(auth_class=Auth())
    @Auth.dag_permission_required
    @marshal_with(ExecutionDetailsEndpointResponse)
    def post(self, idx):
        """
        API method to create a new data check linked to an existing instance
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed, error if data is not validated or
          the reference_id for the newly created execution if successful) and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        config = current_app.config
        user = self.get_user()
        context_str = f"instance {idx}"

        instance = InstanceModel.get_one_object(user=self.get_user(), idx=idx)
        if instance is None:
            err = "The instance to check does not exist"
            raise ObjectDoesNotExist(
                error=err,
                log_txt=f"Error while user {user} tries to run data checks on {context_str}. "
                + err,
            )
        payload = dict(
            config=dict(checks_only=True),
            instance_id=instance.id,
            name=f"data_check_instance_{instance.name}",
            schema=instance.schema,
        )
        schema = instance.schema

        execution, _ = self.post_list(data=payload)

        # this allows testing without airflow interaction:
        if request.args.get("run", "1") == "0":
            execution.update_state(EXEC_STATE_NOT_RUN)
            return execution, 201

        # Initialize Airflow client
        af_client = Airflow.from_config(config)

        # Call the shared Airflow execution logic
        _run_airflow_data_check(af_client, execution, schema, user, context_str)

        current_app.logger.info(
            "User {} creates instance check execution {}".format(
                self.get_user_id(), execution.id
            )
        )
        return execution, 201


class DataCheckCaseEndpoint(BaseMetaResource):
    """
    Endpoint used to execute the instance and solution checks on an execution
    """

    ROLES_WITH_ACCESS = [PLANNER_ROLE, ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.model = ExecutionModel
        self.data_model = ExecutionModel
        self.foreign_data = {"instance_id": InstanceModel}

    @doc(
        description="Create a data check execution for an existing case",
        tags=["Data checks"],
    )
    @authenticate(auth_class=Auth())
    @Auth.dag_permission_required
    @marshal_with(ExecutionDetailsEndpointResponse)
    def post(self, idx):
        """
        API method to create a new data check linked to an existing case
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed, error if data is not validated or
          the reference_id for the newly created execution if successful) and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        config = current_app.config
        user = self.get_user()
        context_str = f"case {idx}"

        case = CaseModel.get_one_object(user=self.get_user(), idx=idx)
        if case is None:
            err = "The case to check does not exist"
            raise ObjectDoesNotExist(
                error=err,
                log_txt=f"Error while user {user} tries to run data checks on {context_str}. "
                + err,
            )

        schema = case.schema or "solve_model_dag"

        instance_payload = dict(
            data=case.data,
            schema=schema,
            name=f"data_check_case_{case.name}",
        )

        self.data_model = InstanceModel
        self.foreign_data = dict()
        if schema is None:
            instance, _ = self.post_list(data=instance_payload)
        else:
            validation_schema = schema
            if schema == "pulp":
                validation_schema = "solve_model_dag"

            data_jsonschema = DeployedDAG.get_one_schema(
                config, validation_schema, INSTANCE_SCHEMA
            )
            validation_errors = json_schema_validate_as_string(
                data_jsonschema, instance_payload["data"]
            )

            if validation_errors:
                raise InvalidData(
                    payload=dict(jsonschema_errors=validation_errors),
                    log_txt=f"Error while user {user} tries to run data checks on {context_str}.  "
                    f"Instance data does not match the jsonschema.",
                )

            instance, _ = self.post_list(data=instance_payload)

        payload = dict(
            config=dict(checks_only=True),
            instance_id=instance.id,
            name=f"data_check_case_{case.name}",
            schema=schema,
        )
        if case.solution is not None:
            validation_schema = schema
            if schema == "pulp":
                validation_schema = "solve_model_dag"

            payload["data"] = case.solution

            data_jsonschema = DeployedDAG.get_one_schema(
                config, validation_schema, SOLUTION_SCHEMA
            )
            validation_errors = json_schema_validate_as_string(
                data_jsonschema, payload["data"]
            )

            if validation_errors:
                raise InvalidData(
                    payload=dict(jsonschema_errors=validation_errors),
                    log_txt=f"Error while user {user} tries to run data checks on {context_str}.  "
                    f"Solution data does not match the jsonschema.",
                )

        self.data_model = ExecutionModel
        self.foreign_data = {"instance_id": InstanceModel}

        execution, _ = self.post_list(data=payload)

        # this allows testing without airflow interaction:
        if request.args.get("run", "1") == "0":
            execution.update_state(EXEC_STATE_NOT_RUN)
            return execution, 201

        # Initialize Airflow client
        af_client = Airflow.from_config(config)

        # Call the shared Airflow execution logic, passing case_id
        _run_airflow_data_check(
            af_client, execution, schema, user, context_str, case_id=idx
        )

        current_app.logger.info(
            "User {} creates case check execution {}".format(
                self.get_user_id(), execution.id
            )
        )
        return execution, 201
