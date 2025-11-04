"""
External endpoints to manage the executions: create new ones, list all of them, get one in particular
or check the status of an ongoing one
These endpoints hve different access url, but manage the same data entities
"""

# Import from libraries
from cornflow_client.airflow.api import Airflow

from cornflow_client.databricks.api import Databricks
from cornflow_client.constants import INSTANCE_SCHEMA, CONFIG_SCHEMA, SOLUTION_SCHEMA
from flask import request, current_app
from flask_apispec import marshal_with, use_kwargs, doc

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import InstanceModel, DeployedWorkflow, ExecutionModel
from cornflow.shared.const import config_orchestrator
from cornflow.schemas.execution import (
    ExecutionDetailsEndpointResponse,
    ExecutionDetailsEndpointWithIndicatorsResponse,
    ExecutionDataEndpointResponse,
    ExecutionLogEndpointResponse,
    ExecutionStatusEndpointResponse,
    ExecutionStatusEndpointUpdate,
    ExecutionRequest,
    ExecutionEditRequest,
    QueryFiltersExecution,
    ReLaunchExecutionRequest,
    ExecutionDetailsWithIndicatorsAndLogResponse,
)
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.compress import compressed
from cornflow.shared.const import (
    AIRFLOW_BACKEND,
    DATABRICKS_BACKEND,
)
from cornflow.shared.const import (
    AIRFLOW_ERROR_MSG,
    AIRFLOW_NOT_REACHABLE_MSG,
    DAG_PAUSED_MSG,
    EXEC_STATE_RUNNING,
    EXEC_STATE_ERROR,
    EXEC_STATE_ERROR_START,
    EXEC_STATE_NOT_RUN,
    EXEC_STATE_UNKNOWN,
    EXECUTION_STATE_MESSAGE_DICT,
    AIRFLOW_TO_STATE_MAP,
    DATABRICKS_TO_STATE_MAP,
    EXEC_STATE_STOPPED,
    EXEC_STATE_QUEUED,
)

from cornflow.shared.exceptions import (
    AirflowError,
    DatabricksError,
    ObjectDoesNotExist,
    InvalidData,
    EndpointNotImplemented,
)
from cornflow.shared.validators import (
    json_schema_validate_as_string,
    json_schema_extend_and_validate_as_string,
)


class OrchestratorMixin(BaseMetaResource):
    """
    Base class that provides orchestrator-related functionality for execution endpoints.
    This mixin handles the initialization and properties for orchestrator clients (Airflow/Databricks).
    """

    def __init__(self):
        super().__init__()
        self._orch_type = None
        self._orch_client = None
        self._orch_error = None
        self._orch_to_state_map = None
        self._orch_const = None

    def _init_orch(self):
        if self._orch_type is None:
            self._orch_type = current_app.config["CORNFLOW_BACKEND"]
            if self._orch_type == AIRFLOW_BACKEND:
                self._orch_client = Airflow.from_config(current_app.config)
                self._orch_error = AirflowError
                self._orch_to_state_map = AIRFLOW_TO_STATE_MAP
                self._orch_const = config_orchestrator["airflow"]
            elif self._orch_type == DATABRICKS_BACKEND:
                self._orch_client = Databricks.from_config(current_app.config)
                self._orch_error = DatabricksError
                self._orch_to_state_map = DATABRICKS_TO_STATE_MAP
                self._orch_const = config_orchestrator["databricks"]

    @property
    def orch_type(self):
        self._init_orch()
        return self._orch_type

    @property
    def orch_client(self):
        self._init_orch()
        return self._orch_client

    @property
    def orch_error(self):
        self._init_orch()
        return self._orch_error

    @property
    def orch_to_state_map(self):
        self._init_orch()
        return self._orch_to_state_map

    @property
    def orch_const(self):
        self._init_orch()
        return self._orch_const


class ExecutionEndpoint(OrchestratorMixin):
    """
    Endpoint used to create a new execution or get all the executions and their information back
    """

    def __init__(self):
        super().__init__()
        self.data_model = ExecutionModel
        self.foreign_data = {"instance_id": InstanceModel}

    @doc(description="Get all executions", tags=["Executions"])
    @authenticate(auth_class=Auth())
    @marshal_with(ExecutionDetailsWithIndicatorsAndLogResponse(many=True))
    @use_kwargs(QueryFiltersExecution, location="query")
    def get(self, **kwargs):
        """
        API method to get all the executions created by the user and its related info
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed or a list with all the executions
          created by the authenticated user) and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        executions = self.get_list(user=self.get_user(), **kwargs)
        current_app.logger.info(f"User {self.get_user()} gets list of executions")

        executions = [
            execution
            for execution in executions
            if not execution.config.get("checks_only", False)
        ]

        running_executions = [
            execution
            for execution in executions
            if execution.state
            in [EXEC_STATE_RUNNING, EXEC_STATE_QUEUED, EXEC_STATE_UNKNOWN]
        ]

        for execution in running_executions:
            run_id = execution.run_id

            if not run_id:
                # it's safe to say we will never get anything if we did not store the run_id
                current_app.logger.warning(
                    "Error while the app tried to update the status of all running executions."
                    f"Execution {execution.id} has status {execution.state} but has no dag run associated."
                )
                continue

            if not self.orch_client.is_alive(config=current_app.config):
                current_app.logger.warning(
                    f"Error while the app tried to update the status of all running executions."
                    f"{AIRFLOW_NOT_REACHABLE_MSG}"
                )
                continue
            try:
                response = self.orch_client.get_run_status(
                    schema=execution.schema, run_id=run_id
                )
            except self.orch_error as err:
                current_app.logger.warning(
                    "Error while the app tried to update the status of all running executions."
                    f"{AIRFLOW_ERROR_MSG} {err}"
                )
                continue
            if self.orch_type == DATABRICKS_BACKEND:
                state = self.orch_to_state_map.get(response, EXEC_STATE_UNKNOWN)
            else:
                data = response.json()
                state = self.orch_to_state_map.get(data["state"], EXEC_STATE_UNKNOWN)
            execution.update_state(state)

        return executions

    @doc(description="Create an execution", tags=["Executions"])
    @authenticate(auth_class=Auth())
    @Auth.dag_permission_required
    @marshal_with(ExecutionDetailsEndpointResponse)
    @use_kwargs(ExecutionRequest, location="json")
    def post(self, **kwargs):
        """
        API method to create a new execution linked to an already existing instance
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed, error if data is not validated or
          the reference_id for the newly created execution if successful) and a integer wit the HTTP status code
        :rtype: Tuple(dict, integer)
        """

        if "schema" not in kwargs:
            kwargs["schema"] = self.orch_const["def_schema"]
        print("Start post execution endpoint")
        current_app.logger.info("Start post execution endpoint")
        # region INDEPENDIENTE A AIRFLOW
        config = current_app.config
        execution, status_code = self.post_list(data=kwargs)
        # Users can access all objects
        print(f"execution: {execution}")
        current_app.logger.info(f"execution: {execution}")
        print(f"execution.instance_id: {execution.instance_id}")
        current_app.logger.info(f"execution.instance_id: {execution.instance_id}")
        instance = InstanceModel.get_one_object(idx=execution.instance_id)
        print(f"instance: {instance}")
        current_app.logger.info(f"instance: {instance}")
        print(f"instance.id: {instance.id}")
        current_app.logger.info(f"instance.id: {instance.id}")
        current_app.logger.info(f"Instance {instance} to be executed is {instance.id}")

        if execution.schema != instance.schema:
            execution.delete()
            raise InvalidData(error="Instance and execution schema mismatch")

        current_app.logger.debug(f"The request is: {request.args.get('run')}")
        # this allows testing without  orchestrator interaction:
        if request.args.get("run", "1") == "0":
            current_app.logger.info(
                f"User {self.get_user_id()} creates execution {execution.id} but does not run it."
            )
            execution.update_state(EXEC_STATE_NOT_RUN)
            return execution, 201

        # We now try to launch the task in the orchestrator
        # Note schema is a string with the name of the job/dag
        schema = execution.schema
        # endregion

        # region VALIDACIONES
        # We check if the job/dag exists and orchestrator is alive
        if not self.orch_client.is_alive(config=current_app.config):
            error = f"{self.orch_const['name']} is not accessible"
            current_app.logger.error(error)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise self.orch_error(
                error=error,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    state=EXEC_STATE_ERROR_START,
                ),
                log_txt=f"Error while user {self.get_user()} tries to create an execution. "
                + error,
            )

        schema_info = self.orch_client.get_workflow_info(workflow_name=schema)
        # Validate config before running the run
        config_schema = DeployedWorkflow.get_one_schema(config, schema, CONFIG_SCHEMA)
        new_config, config_errors = json_schema_extend_and_validate_as_string(
            config_schema, kwargs["config"]
        )
        if config_errors:
            execution.update_state(
                EXEC_STATE_ERROR_START,
                message="The execution could not be run because the config does not comply with the json schema. "
                "Check the log for more details",
            )
            execution.update_log_txt(f"{config_errors}")
            raise InvalidData(
                payload=dict(jsonschema_errors=config_errors),
                log_txt=f"Error while user {self.get_user()} tries to create an execution. "
                f"Configuration data does not match the jsonschema.",
            )
        elif new_config != kwargs["config"]:
            execution.update_config(new_config)

        # Validate instance data before running the dag
        instance_schema = DeployedWorkflow.get_one_schema(
            config, schema, INSTANCE_SCHEMA
        )
        instance_errors = json_schema_validate_as_string(instance_schema, instance.data)
        if instance_errors:
            execution.update_state(
                EXEC_STATE_ERROR_START,
                message="The execution could not be run because the instance data does not "
                "comply with the json schema. Check the log for more details",
            )
            execution.update_log_txt(f"{instance_errors}")
            raise InvalidData(
                payload=dict(jsonschema_errors=instance_errors),
                log_txt=f"Error while user {self.get_user()} tries to create an execution. "
                f"Instance data does not match the jsonschema.",
            )
        # Validate solution data before running the dag (if it exists)
        if kwargs.get("data") is not None:
            solution_schema = DeployedWorkflow.get_one_schema(
                config, schema, SOLUTION_SCHEMA
            )
            solution_errors = json_schema_validate_as_string(
                solution_schema, kwargs["data"]
            )
            if solution_errors:
                execution.update_state(
                    EXEC_STATE_ERROR_START,
                    message="The execution could not be run because the solution data does not "
                    "comply with the json schema. Check the log for more details",
                )
                execution.update_log_txt(f"{solution_errors}")
                raise InvalidData(payload=dict(jsonschema_errors=solution_errors))
        # endregion
        # TODO: Consider adding similar checks for databricks
        if self.orch_type == AIRFLOW_BACKEND:
            info = schema_info.json()
            if info["is_paused"]:
                current_app.logger.error(DAG_PAUSED_MSG)
                execution.update_state(EXEC_STATE_ERROR_START)
                raise self.orch_error(
                    error=DAG_PAUSED_MSG,
                    payload=dict(
                        message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                        state=EXEC_STATE_ERROR_START,
                    ),
                    log_txt=f"Error while user {self.get_user()} tries to create an execution. "
                    + DAG_PAUSED_MSG,
                )

        try:
            response = self.orch_client.run_workflow(execution.id, workflow_name=schema)
        except self.orch_error as err:
            error = self.orch_const["name"] + " responded with an error: {}".format(err)
            current_app.logger.error(error)
            execution.update_state(EXEC_STATE_ERROR)
            raise self.orch_error(
                error=error,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                    state=EXEC_STATE_ERROR,
                ),
                log_txt=f"Error while user {self.get_user()} tries to create an execution. "
                + error,
            )

        # if we succeed, we register the run_id in the execution table:
        orch_data = response.json()
        info = "orch data is " + str(orch_data)
        current_app.logger.info(info)
        execution.run_id = orch_data[self.orch_const["run_id"]]
        execution.update_state(EXEC_STATE_QUEUED)
        current_app.logger.info(
            "User {} creates execution {}".format(self.get_user_id(), execution.id)
        )
        return execution, 201


class ExecutionRelaunchEndpoint(OrchestratorMixin):
    def __init__(self):
        super().__init__()
        self.model = ExecutionModel
        self.data_model = ExecutionModel
        self.foreign_data = {"instance_id": InstanceModel}

    @doc(description="Re-launch an execution", tags=["Executions"])
    @authenticate(auth_class=Auth())
    @Auth.dag_permission_required
    @use_kwargs(ReLaunchExecutionRequest, location="json")
    def post(self, idx, **kwargs):
        """
        API method to re-launch an existing execution
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed, error if data is not validated or
          the reference_id for the newly created execution if successful) and a integer wit the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        config = current_app.config
        if "schema" not in kwargs:
            kwargs["schema"] = self.orch_const["def_schema"]

        self.put_detail(
            data=dict(config=kwargs["config"]), user=self.get_user(), idx=idx
        )

        execution = ExecutionModel.get_one_object(user=self.get_user(), idx=idx)

        # If the execution does not exist, raise an error
        if execution is None:
            err = "The execution to re-solve does not exist"
            raise ObjectDoesNotExist(
                err,
                log_txt=f"Error while user {self.get_user()} tries to relaunch execution {idx}. "
                + err,
            )

        execution.update({"checks": None})

        # If the execution is still running or queued, raise an error
        if execution.state == 0 or execution.state == -7:
            return {"message": "This execution is still running"}, 400

        # this allows testing without airflow interaction:
        if request.args.get("run", "1") == "0":
            execution.update_state(EXEC_STATE_NOT_RUN)
            return {
                "message": "The execution was set for relaunch but was not launched"
            }, 201

        # Validate config before running the dag
        config_schema = DeployedWorkflow.get_one_schema(
            config, kwargs["schema"], CONFIG_SCHEMA
        )
        config_errors = json_schema_validate_as_string(config_schema, kwargs["config"])
        if config_errors:
            raise InvalidData(
                payload=dict(jsonschema_errors=config_errors),
                log_txt=f"Error while user {self.get_user()} tries to relaunch execution {idx}. "
                f"Configuration data does not match the jsonschema.",
            )
        schema = execution.schema

        # Check if orchestrator is alive
        if not self.orch_client.is_alive(config=current_app.config):
            error = f"{self.orch_const['name']} is not accessible"
            current_app.logger.error(error)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise self.orch_error(
                error=error,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    state=EXEC_STATE_ERROR_START,
                ),
                log_txt=f"Error while user {self.get_user()} tries to relaunch execution {idx}. "
                + error,
            )

        schema_info = self.orch_client.get_workflow_info(workflow_name=schema)
        info = schema_info.json()
        if self.orch_type == AIRFLOW_BACKEND:
            if info["is_paused"]:
                current_app.logger.error(AIRFLOW_NOT_REACHABLE_MSG)
                execution.update_state(EXEC_STATE_ERROR_START)
                raise self.orch_error(
                    error=AIRFLOW_NOT_REACHABLE_MSG,
                    payload=dict(
                        message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                        state=EXEC_STATE_ERROR_START,
                    ),
                    log_txt=f"Error while user {self.get_user()} tries to relaunch execution {idx}. "
                    + AIRFLOW_NOT_REACHABLE_MSG,
                )
        # TODO: Consider adding similar checks for databricks
        try:
            response = self.orch_client.run_workflow(execution.id, workflow_name=schema)
        except self.orch_error as err:
            error = self.orch_const["name"] + " responded with an error: {}".format(err)
            current_app.logger.error(error)
            execution.update_state(EXEC_STATE_ERROR)
            raise self.orch_error(
                error=error,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                    state=EXEC_STATE_ERROR,
                ),
                log_txt=f"Error while user {self.get_user()} tries to relaunch execution {idx}. "
                + error,
            )

        # if we succeed, we register the run_id in the execution table:
        orch_data = response.json()
        execution.run_id = orch_data[self.orch_const["run_id"]]
        execution.update_state(EXEC_STATE_QUEUED)
        current_app.logger.info(
            "User {} relaunches execution {}".format(self.get_user_id(), execution.id)
        )
        return {"message": "The execution was relaunched correctly"}, 201


class ExecutionDetailsEndpointBase(OrchestratorMixin):
    """
    Endpoint used to get the information of a certain execution. But not the data!
    """

    def __init__(self):
        super().__init__()
        self.data_model = ExecutionModel
        self.foreign_data = {"instance_id": InstanceModel}


class ExecutionDetailsEndpoint(ExecutionDetailsEndpointBase):
    @doc(description="Get details of an execution", tags=["Executions"], inherit=False)
    @authenticate(auth_class=Auth())
    @marshal_with(ExecutionDetailsEndpointWithIndicatorsResponse)
    @BaseMetaResource.get_data_or_404
    def get(self, idx):
        """
        API method to get an execution created by the user and its related info.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the execution) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        current_app.logger.info(
            f"User {self.get_user()} gets details of execution {idx}"
        )
        return self.get_detail(user=self.get_user(), idx=idx)

    @doc(description="Edit an execution", tags=["Executions"], inherit=False)
    @authenticate(auth_class=Auth())
    @use_kwargs(ExecutionEditRequest, location="json")
    def put(self, idx, **data):
        """
        Edit an existing execution

        :param string idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        config = current_app.config

        schema = ExecutionModel.get_one_object(user=self.get_user(), idx=idx).schema

        if data.get("data") is not None and schema is not None:
            data_jsonschema = DeployedWorkflow.get_one_schema(
                config, schema, SOLUTION_SCHEMA
            )
            validation_errors = json_schema_validate_as_string(
                data_jsonschema, data["data"]
            )

            if validation_errors:
                raise InvalidData(
                    payload=dict(jsonschema_errors=validation_errors),
                    log_txt=f"Error while user {self.get_user()} tries to edit execution {idx}. "
                    f"Solution data does not match the jsonschema.",
                )

        current_app.logger.info(f"User {self.get_user()} edits execution {idx}")
        return self.put_detail(data, user=self.get_user(), idx=idx)

    @doc(description="Delete an execution", tags=["Executions"], inherit=False)
    @authenticate(auth_class=Auth())
    def delete(self, idx):
        """
        API method to delete an execution created by the user and its related info.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param string idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        current_app.logger.info(f"User {self.get_user()} deleted execution {idx}")
        return self.delete_detail(user=self.get_user(), idx=idx)

    @doc(description="Stop an execution", tags=["Executions"], inherit=False)
    @authenticate(auth_class=Auth())
    @Auth.dag_permission_required
    def post(self, idx):
        if self.orch_type != AIRFLOW_BACKEND:
            return {
                "message": f"This feature is not available for {self.orch_const['name']}"
            }, 501
        execution = ExecutionModel.get_one_object(user=self.get_user(), idx=idx)
        if execution is None:
            raise ObjectDoesNotExist(
                log_txt=f"Error while user {self.get_user()} tries to stop execution {idx}. "
                f"The execution does not exist."
            )

        if not self.orch_client.is_alive(config=current_app.config):
            raise self.orch_error(
                error=AIRFLOW_NOT_REACHABLE_MSG,
                log_txt=f"Error while user {self.get_user()} tries to stop execution {idx}. {AIRFLOW_NOT_REACHABLE_MSG}",
            )

        self.orch_client.set_dag_run_to_fail(
            dag_name=execution.schema, run_id=execution.run_id
        )
        # We should check if the execution has been stopped
        execution.update_state(EXEC_STATE_STOPPED)
        current_app.logger.info(f"User {self.get_user()} stopped execution {idx}")
        return {"message": "The execution has been stopped"}, 200


class ExecutionStatusEndpoint(OrchestratorMixin):
    """
    Endpoint used to get the status of a certain execution that is running in the airflow webserver
    """

    def __init__(self):
        super().__init__()
        self.data_model = ExecutionModel

    @doc(description="Get status of an execution", tags=["Executions"])
    @authenticate(auth_class=Auth())
    @marshal_with(ExecutionStatusEndpointResponse)
    def get(self, idx):
        """
        API method to get the status of the execution created by the user
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param str idx:  ID of the execution
        :return: A dictionary with a message (error if the execution does not exist or status of the execution)
            and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        execution = self.data_model.get_one_object(user=self.get_user(), idx=idx)
        if execution is None:
            raise ObjectDoesNotExist(
                log_txt=f"Error while user {self.get_user()} tries to get the status of execution {idx}. "
                f"The execution does not exist."
            )
        if execution.state not in [
            EXEC_STATE_RUNNING,
            EXEC_STATE_QUEUED,
            EXEC_STATE_UNKNOWN,
        ]:
            # we only care on asking orchestrator if the status is unknown, queued or running.
            return execution, 200

        def _raise_af_error(execution, error, state=EXEC_STATE_UNKNOWN, log_txt=None):
            if log_txt is None:
                log_txt = error
            message = EXECUTION_STATE_MESSAGE_DICT[state]
            execution.update_state(state)
            raise self.orch_error(
                error=error, payload=dict(message=message, state=state), log_txt=log_txt
            )

        run_id = execution.run_id
        if not run_id:
            # it's safe to say we will never get anything if we did not store the run_id
            _raise_af_error(
                execution,
                state=EXEC_STATE_ERROR,
                error="The execution has no run_id associated",
                log_txt=f"Error while user {self.get_user()} tries to get the status of execution {idx}. "
                f"The execution has no associated run id.",
            )
        schema = execution.schema
        # We check if the orchestrator is alive
        if not self.orch_client.is_alive(config=current_app.config):
            error = f"{self.orch_const['name']} is not accessible"
            _raise_af_error(
                execution,
                error,
                state=EXEC_STATE_ERROR_START,
                log_txt=f"Error while user {self.get_user()} tries to get the status of execution {idx}. "
                + error,
            )
        try:
            state = self.orch_client.get_run_status(schema, run_id)
        except self.orch_error as err:
            error = self.orch_const["name"] + f" responded with an error: {err}"
            _raise_af_error(
                execution,
                error,
                log_txt=f"Error while user {self.get_user()} tries to get the status of execution {idx}. "
                + str(err),
            )

        state = map_run_state(state, self.orch_type)
        execution.update_state(state)
        current_app.logger.info(
            f"User {self.get_user()} gets status of execution {idx}"
        )
        return execution, 200

    @doc(description="Change status of an execution", tags=["Executions"])
    @authenticate(auth_class=Auth())
    @use_kwargs(ExecutionStatusEndpointUpdate)
    def put(self, idx, **data):
        """
        Edit an existing execution

        :param string idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """

        execution = self.data_model.get_one_object(user=self.get_user(), idx=idx)
        if execution is None:
            raise ObjectDoesNotExist()
        if execution.state not in [
            EXEC_STATE_RUNNING,
            EXEC_STATE_UNKNOWN,
            EXEC_STATE_QUEUED,
        ]:
            # we only care on asking airflow if the status is unknown or is running.
            return {"message": f"execution {idx} updated correctly"}, 200
        state = data.get("status")
        if state is not None:
            execution.update_state(state)
            current_app.logger.info(f"User {self.get_user()} edits execution {idx}")
            return {"message": f"execution {idx} updated correctly"}, 200
        else:
            return {"error": "status code was missing"}, 400


class ExecutionDataEndpoint(ExecutionDetailsEndpointBase):
    """
    Endpoint used to get the solution of a certain execution.
    """

    @doc(
        description="Get solution data of an execution",
        tags=["Executions"],
        inherit=False,
    )
    @authenticate(auth_class=Auth())
    @marshal_with(ExecutionDataEndpointResponse)
    @BaseMetaResource.get_data_or_404
    @compressed
    def get(self, idx):
        """

        :param str idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the execution) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        current_app.logger.info(f"User {self.get_user()} gets data of execution {idx}")
        return self.get_detail(user=self.get_user(), idx=idx)


class ExecutionLogEndpoint(ExecutionDetailsEndpointBase):
    """
    Endpoint used to get the log of a certain execution.
    """

    @doc(description="Get log of an execution", tags=["Executions"], inherit=False)
    @authenticate(auth_class=Auth())
    @marshal_with(ExecutionLogEndpointResponse)
    @BaseMetaResource.get_data_or_404
    @compressed
    def get(self, idx):
        """

        :param str idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the execution) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        current_app.logger.info(f"User {self.get_user()} gets log of execution {idx}")
        return self.get_detail(user=self.get_user(), idx=idx)


# region aux_functions


def map_run_state(state, orch_TYPE):
    """
    Maps the state of the execution in the orchestrator to the state of the execution in cornflow
    """
    if orch_TYPE == AIRFLOW_BACKEND:
        state = state.json()["state"]
        return AIRFLOW_TO_STATE_MAP.get(state, EXEC_STATE_UNKNOWN)
    elif orch_TYPE == DATABRICKS_BACKEND:
        preliminar_state = DATABRICKS_TO_STATE_MAP.get(state, EXEC_STATE_UNKNOWN)
        return preliminar_state
