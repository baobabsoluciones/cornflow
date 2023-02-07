"""
External endpoints to manage the executions: create new ones, list all of them, get one in particular
or check the status of an ongoing one
These endpoints hve different access url, but manage the same data entities
"""

# Import from libraries
from cornflow_client.airflow.api import Airflow, get_schema
from cornflow_core.resources import BaseMetaResource
from cornflow_core.shared import (
    validate_and_continue,
    marshmallow_validate_and_continue,
    json_schema_validate_as_string
)
from cornflow_client.constants import (
    INSTANCE_SCHEMA,
    CONFIG_SCHEMA,
    SOLUTION_SCHEMA
)
from flask import request, current_app
from flask_apispec import marshal_with, use_kwargs, doc
import logging as log

# Import from internal modules
from ..models import InstanceModel, DeployedDAG, ExecutionModel
from ..schemas.execution import (
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
)

from ..shared.authentication import Auth
from ..shared.const import (
    EXEC_STATE_RUNNING,
    EXEC_STATE_ERROR,
    EXEC_STATE_ERROR_START,
    EXEC_STATE_NOT_RUN,
    EXEC_STATE_UNKNOWN,
    EXECUTION_STATE_MESSAGE_DICT,
    AIRFLOW_TO_STATE_MAP,
    EXEC_STATE_STOPPED,
    EXEC_STATE_QUEUED,
)
from cornflow_core.authentication import authenticate
from cornflow_core.exceptions import AirflowError, ObjectDoesNotExist, InvalidData
from cornflow_core.compress import compressed


class ExecutionEndpoint(BaseMetaResource):
    """
    Endpoint used to create a new execution or get all the executions and their information back
    """

    def __init__(self):
        super().__init__()
        self.model = ExecutionModel
        self.data_model = ExecutionModel
        self.foreign_data = {"instance_id": InstanceModel}

    @doc(description="Get all executions", tags=["Executions"])
    @authenticate(auth_class=Auth())
    @marshal_with(ExecutionDetailsEndpointWithIndicatorsResponse(many=True))
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
        return [
            execution
            for execution in executions
            if not execution.config.get("checks_only", False)
        ]

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
        # TODO: should validation should be done even if the execution is not going to be run?
        # TODO: should the schema field be cross validated with the instance schema field?
        config = current_app.config

        if "schema" not in kwargs:
            kwargs["schema"] = "solve_model_dag"

        if kwargs.get("data") is not None:
            # Get solution schema and validate it
            marshmallow_obj = get_schema(config, kwargs["schema"], "solution")
            marshmallow_validate_and_continue(marshmallow_obj(), kwargs["data"])

        execution, status_code = self.post_list(data=kwargs)
        instance = InstanceModel.get_one_object(
            user=self.get_user(), idx=execution.instance_id
        )

        if instance is None:
            raise ObjectDoesNotExist(error="The instance to solve does not exist")

        log.debug(f"The request is: {request.args.get('run')}")
        # this allows testing without airflow interaction:
        if request.args.get("run", "1") == "0":
            execution.update_state(EXEC_STATE_NOT_RUN)
            return execution, 201

        # We now try to launch the task in airflow
        af_client = Airflow.from_config(config)
        if not af_client.is_alive():
            err = "Airflow is not accessible"
            log.error(err)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise AirflowError(
                error=err,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    state=EXEC_STATE_ERROR_START,
                ),
            )
        # ask airflow if dag_name exists
        schema = execution.schema
        schema_info = af_client.get_dag_info(schema)

        # Validate config before running the dag
        config_schema = af_client.get_one_schema(schema, CONFIG_SCHEMA)
        # config_schema = DeployedDAG.get_one_schema(config, schema, CONFIG_SCHEMA)
        config_errors = json_schema_validate_as_string(config_schema, kwargs["config"])
        if config_errors:
            execution.update_state(
                EXEC_STATE_ERROR_START,
                message="The execution could not be run because the config does not comply with the json schema. "
                "Check the log for more details",
            )
            execution.update_log_txt(f"{config_errors}")
            current_app.logger.warning(f"{config_errors}")
            raise InvalidData(payload=dict(jsonschema_errors=config_errors))

        # # Get dag config schema and validate it
        # marshmallow_obj = get_schema(config, schema, "config")
        # validate_and_continue(marshmallow_obj(), kwargs["config"])

        # Validate instance data before running the dag
        instance_schema = DeployedDAG.get_one_schema(config, schema, INSTANCE_SCHEMA)
        instance_errors = json_schema_validate_as_string(instance_schema, instance.data)
        if instance_errors:
            execution.update_state(
                EXEC_STATE_ERROR_START,
                message="The execution could not be run because the instance data does not "
                "comply with the json schema. Check the log for more details",
            )
            execution.update_log_txt(f"{instance_errors}")
            raise InvalidData(payload=dict(jsonschema_errors=instance_errors))

        # Validate solution data before running the dag (if it exists)
        if kwargs.get("data") is not None:
            solution_schema = DeployedDAG.get_one_schema(config, schema, SOLUTION_SCHEMA)
            solution_errors = json_schema_validate_as_string(solution_schema, kwargs["data"])
            if solution_errors:
                execution.update_state(
                    EXEC_STATE_ERROR_START,
                    message="The execution could not be run because the solution data does not "
                    "comply with the json schema. Check the log for more details",
                )
                execution.update_log_txt(f"{solution_errors}")
                raise InvalidData(payload=dict(jsonschema_errors=solution_errors))

        # # Validate that instance and dag_name are compatible
        # marshmallow_obj = get_schema(config, schema, INSTANCE_SCHEMA)
        # validate_and_continue(marshmallow_obj(), instance.data)

        info = schema_info.json()
        if info["is_paused"]:
            err = "The dag exists but it is paused in airflow"
            log.error(err)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise AirflowError(
                error=err,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    state=EXEC_STATE_ERROR_START,
                ),
            )

        try:
            response = af_client.run_dag(execution.id, dag_name=schema)
        except AirflowError as err:
            error = "Airflow responded with an error: {}".format(err)
            log.error(error)
            execution.update_state(EXEC_STATE_ERROR)
            raise AirflowError(
                error=error,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                    state=EXEC_STATE_ERROR,
                ),
            )

        # if we succeed, we register the dag_run_id in the execution table:
        af_data = response.json()
        execution.dag_run_id = af_data["dag_run_id"]
        execution.update_state(EXEC_STATE_QUEUED)
        log.info(
            "User {} creates execution {}".format(self.get_user_id(), execution.id)
        )
        return execution, 201


class ExecutionRelaunchEndpoint(BaseMetaResource):
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
            kwargs["schema"] = "solve_model_dag"

        self.put_detail(
            data=dict(config=kwargs["config"]), user=self.get_user(), idx=idx
        )

        execution = ExecutionModel.get_one_object(user=self.get_user(), idx=idx)

        # If the execution does not exist, raise an error
        if execution is None:
            raise ObjectDoesNotExist("The execution to re-solve does not exist")

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

        # Get dag config schema and validate it
        marshmallow_obj = DeployedDAG.get_marshmallow_schema(config, kwargs["schema"], "config")
        validate_and_continue(marshmallow_obj(), kwargs["config"])

        # We now try to launch the task in airflow
        af_client = Airflow.from_config(config)
        if not af_client.is_alive():
            err = "Airflow is not accessible"
            log.error(err)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise AirflowError(
                error=err,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    state=EXEC_STATE_ERROR_START,
                ),
            )
        # ask airflow if dag_name exists
        schema = execution.schema
        schema_info = af_client.get_dag_info(schema)

        info = schema_info.json()
        if info["is_paused"]:
            err = "The dag exists but it is paused in airflow"
            log.error(err)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise AirflowError(
                error=err,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    state=EXEC_STATE_ERROR_START,
                ),
            )

        try:
            response = af_client.run_dag(execution.id, dag_name=schema)
        except AirflowError as err:
            error = "Airflow responded with an error: {}".format(err)
            log.error(error)
            execution.update_state(EXEC_STATE_ERROR)
            raise AirflowError(
                error=error,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                    state=EXEC_STATE_ERROR,
                ),
            )

        # if we succeed, we register the dag_run_id in the execution table:
        af_data = response.json()
        execution.dag_run_id = af_data["dag_run_id"]
        execution.update_state(EXEC_STATE_QUEUED)
        log.info(
            "User {} creates execution {}".format(self.get_user_id(), execution.id)
        )
        return {"message": "The execution was relaunched correctly"}, 201


class ExecutionDetailsEndpointBase(BaseMetaResource):
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
            # Get solution schema and validate it
            try:
                marshmallow_obj = DeployedDAG.get_marshmallow_schema(config, schema, "solution")
                validate_and_continue(marshmallow_obj(), data["data"])
            except AirflowError:
                # This is for the unit tests when we can't use Airflow
                pass

        log.info(f"User {self.get_user()} edits execution {idx}")
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
        log.info(f"User {self.get_user()} deleted execution {idx}")
        return self.delete_detail(user=self.get_user(), idx=idx)

    @doc(description="Stop an execution", tags=["Executions"], inherit=False)
    @authenticate(auth_class=Auth())
    @Auth.dag_permission_required
    def post(self, idx):
        execution = ExecutionModel.get_one_object(user=self.get_user(), idx=idx)
        if execution is None:
            raise ObjectDoesNotExist()
        af_client = Airflow.from_config(current_app.config)
        if not af_client.is_alive():
            raise AirflowError(error="Airflow is not accessible")
        response = af_client.set_dag_run_to_fail(
            dag_name=execution.schema, dag_run_id=execution.dag_run_id
        )
        execution.update_state(EXEC_STATE_STOPPED)
        log.info(f"User {self.get_user()} stopped execution {idx}")
        return {"message": "The execution has been stopped"}, 200


class ExecutionStatusEndpoint(BaseMetaResource):
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
            raise ObjectDoesNotExist()
        if execution.state not in [
            EXEC_STATE_RUNNING,
            EXEC_STATE_QUEUED,
            EXEC_STATE_UNKNOWN,
        ]:
            # we only care on asking airflow if the status is unknown, queued or running.
            return execution, 200

        def _raise_af_error(execution, error, state=EXEC_STATE_UNKNOWN):
            message = EXECUTION_STATE_MESSAGE_DICT[state]
            execution.update_state(state)
            raise AirflowError(error=error, payload=dict(message=message, state=state))

        dag_run_id = execution.dag_run_id
        if not dag_run_id:
            # it's safe to say we will never get anything if we did not store the dag_run_id
            _raise_af_error(
                execution,
                state=EXEC_STATE_ERROR,
                error="The execution has no dag_run associated",
            )

        af_client = Airflow.from_config(current_app.config)
        if not af_client.is_alive():
            _raise_af_error(execution, "Airflow is not accessible")

        try:
            # TODO: get the dag_name from somewhere!
            response = af_client.get_dag_run_status(
                dag_name=execution.schema, dag_run_id=dag_run_id
            )
        except AirflowError as err:
            _raise_af_error(execution, f"Airflow responded with an error: {err}")

        data = response.json()
        state = AIRFLOW_TO_STATE_MAP.get(data["state"], EXEC_STATE_UNKNOWN)
        execution.update_state(state)
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
            log.info(f"User {self.get_user()} edits execution {idx}")
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
        return self.get_detail(user=self.get_user(), idx=idx)
