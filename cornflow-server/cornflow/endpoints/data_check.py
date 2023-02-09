"""
External endpoints to launch the solution check on an execution
"""

# Import from libraries
from cornflow_client.airflow.api import Airflow, get_schema
from cornflow_core.resources import BaseMetaResource
from cornflow_core.shared import validate_and_continue
from flask import request, current_app
from flask_apispec import marshal_with, doc

# Import from internal modules
from ..models import InstanceModel, ExecutionModel, CaseModel, DeployedDAG
from ..schemas.execution import ExecutionDetailsEndpointResponse
from ..schemas.model_json import DataSchema

from ..shared.authentication import Auth
from ..shared.const import (
    EXEC_STATE_QUEUED,
    EXEC_STATE_ERROR,
    EXEC_STATE_ERROR_START,
    EXEC_STATE_NOT_RUN,
    EXECUTION_STATE_MESSAGE_DICT,
)
from cornflow_core.authentication import authenticate
from cornflow_core.exceptions import AirflowError, ObjectDoesNotExist, InvalidUsage


class DataCheckExecutionEndpoint(BaseMetaResource):
    """
    Endpoint used to execute the instance and solution checks on an execution
    """

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

        execution = ExecutionModel.get_one_object(user=self.get_user(), idx=idx)
        if execution is None:
            err = "The execution to check does not exist"
            raise ObjectDoesNotExist(
                error=err,
                log_txt=f"Error while user {self.get_user()} tries to run data checks on execution {idx}. " + err
            )

        schema = execution.schema

        # If the execution is still running or queued, raise an error
        if execution.state == 0 or execution.state == -7:
            err = "The execution is still running"
            raise InvalidUsage(
                error=err,
                log_txt=f"Error while user {self.get_user()} tries to run data checks on execution {idx}. " + err
            )

        # this allows testing without airflow interaction:
        if request.args.get("run", "1") == "0":
            execution.update_state(EXEC_STATE_NOT_RUN)
            return execution, 201

        # We now try to launch the task in airflow
        af_client = Airflow.from_config(config)
        if not af_client.is_alive():
            err = "Airflow is not accessible"
            current_app.logger.error(err)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise AirflowError(
                error=err,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    state=EXEC_STATE_ERROR_START,
                ),
                log_txt=f"Error while user {self.get_user()} tries to run data checks on execution {idx}. " + err
            )
        # ask airflow if dag_name exists
        schema_info = af_client.get_dag_info(schema)

        info = schema_info.json()
        if info["is_paused"]:
            err = "The dag exists but it is paused in airflow"
            current_app.logger.error(err)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise AirflowError(
                error=err,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    state=EXEC_STATE_ERROR_START,
                ),
                log_txt=f"Error while user {self.get_user()} tries to run data checks on execution {idx}. " + err
            )

        try:
            response = af_client.run_dag(
                execution.id, dag_name=schema, checks_only=True
            )
        except AirflowError as err:
            error = "Airflow responded with an error: {}".format(err)
            current_app.logger.error(error)
            execution.update_state(EXEC_STATE_ERROR)
            raise AirflowError(
                error=error,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                    state=EXEC_STATE_ERROR,
                ),
                log_txt=f"Error while user {self.get_user()} tries to run data checks on execution {idx}. " + error
            )

        # if we succeed, we register the dag_run_id in the execution table:
        af_data = response.json()
        execution.dag_run_id = af_data["dag_run_id"]
        execution.update_state(EXEC_STATE_QUEUED)
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

        instance = InstanceModel.get_one_object(user=self.get_user(), idx=idx)
        if instance is None:
            err = "The instance to check does not exist"
            raise ObjectDoesNotExist(
                error=err,
                log_txt=f"Error while user {self.get_user()} tries to run data checks on instance {idx}. " + err
            )
        payload = dict(
            config=dict(checks_only=True),
            instance_id=instance.id,
            name=f"data_check_instance_{instance.name}",
            schema=instance.schema,
        )
        schema = instance.schema

        execution, status_code = self.post_list(data=payload)

        # this allows testing without airflow interaction:
        if request.args.get("run", "1") == "0":
            execution.update_state(EXEC_STATE_NOT_RUN)
            return execution, 201

        # We now try to launch the task in airflow
        af_client = Airflow.from_config(config)
        if not af_client.is_alive():
            err = "Airflow is not accessible"
            current_app.logger.error(err)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise AirflowError(
                error=err,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    state=EXEC_STATE_ERROR_START,
                ),
                log_txt=f"Error while user {self.get_user()} tries to run data checks on instance {idx}. " + err

            )
        # ask airflow if dag_name exists
        schema_info = af_client.get_dag_info(schema)

        info = schema_info.json()
        if info["is_paused"]:
            err = "The dag exists but it is paused in airflow"
            current_app.logger.error(err)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise AirflowError(
                error=err,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    state=EXEC_STATE_ERROR_START,
                ),
                log_txt=f"Error while user {self.get_user()} tries to run data checks on instance {idx}. " + err

            )

        try:
            response = af_client.run_dag(
                execution.id, dag_name=schema, checks_only=True
            )
        except AirflowError as err:
            error = "Airflow responded with an error: {}".format(err)
            current_app.logger.error(error)
            execution.update_state(EXEC_STATE_ERROR)
            raise AirflowError(
                error=error,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                    state=EXEC_STATE_ERROR,
                ),
                log_txt=f"Error while user {self.get_user()} tries to run data checks on instance {idx}. " + error
            )

        # if we succeed, we register the dag_run_id in the execution table:
        af_data = response.json()
        execution.dag_run_id = af_data["dag_run_id"]
        execution.update_state(EXEC_STATE_QUEUED)
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

        case = CaseModel.get_one_object(user=self.get_user(), idx=idx)
        if case is None:
            err = "The case to check does not exist"
            raise ObjectDoesNotExist(
                error=err,
                log_txt=f"Error while user {self.get_user()} tries to run data checks on case {idx}. " + err
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
        elif schema == "pulp" or schema == "solve_model_dag":
            validate_and_continue(DataSchema(), instance_payload["data"])
            instance, _ = self.post_list(data=instance_payload)
        else:
            marshmallow_obj = DeployedDAG.get_marshmallow_schema(config, schema)
            validate_and_continue(marshmallow_obj(), instance_payload["data"])
            instance, _ = self.post_list(data=instance_payload)

        payload = dict(
            config=dict(checks_only=True),
            instance_id=instance.id,
            name=f"data_check_case_{case.name}",
            schema=schema,
        )
        if case.solution is not None:
            payload["data"] = case.solution

            marshmallow_obj = DeployedDAG.get_marshmallow_schema(config, schema, "solution")
            validate_and_continue(marshmallow_obj(), payload["data"])

        self.data_model = ExecutionModel
        self.foreign_data = {"instance_id": InstanceModel}

        execution, _ = self.post_list(data=payload)

        # this allows testing without airflow interaction:
        if request.args.get("run", "1") == "0":
            execution.update_state(EXEC_STATE_NOT_RUN)
            return execution, 201

        # We now try to launch the task in airflow
        af_client = Airflow.from_config(config)
        if not af_client.is_alive():
            err = "Airflow is not accessible"
            current_app.logger.error(err)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise AirflowError(
                error=err,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    state=EXEC_STATE_ERROR_START,
                ),
                log_txt=f"Error while user {self.get_user()} tries to run data checks on case {idx}. " + err
            )
        # ask airflow if dag_name exists
        schema_info = af_client.get_dag_info(schema)

        info = schema_info.json()
        if info["is_paused"]:
            err = "The dag exists but it is paused in airflow"
            current_app.logger.error(err)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise AirflowError(
                error=err,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    state=EXEC_STATE_ERROR_START,
                ),
                log_txt=f"Error while user {self.get_user()} tries to run data checks on case {idx}. " + err
            )

        try:
            response = af_client.run_dag(
                execution.id, dag_name=schema, checks_only=True, case_id=idx
            )

        except AirflowError as err:
            error = "Airflow responded with an error: {}".format(err)
            current_app.logger.error(error)
            execution.update_state(EXEC_STATE_ERROR)
            raise AirflowError(
                error=error,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                    state=EXEC_STATE_ERROR,
                ),
                log_txt=f"Error while user {self.get_user()} tries to run data checks on case {idx}. " + error
            )

        # if we succeed, we register the dag_run_id in the execution table:
        af_data = response.json()
        execution.dag_run_id = af_data["dag_run_id"]
        execution.update_state(EXEC_STATE_QUEUED)
        current_app.logger.info(
            "User {} creates case check execution {}".format(
                self.get_user_id(), execution.id
            )
        )
        return execution, 201
