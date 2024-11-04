"""
External endpoints to manage the executions: create new ones, list all of them, get one in particular
or check the status of an ongoing one
These endpoints hve different access url, but manage the same data entities
"""

# Import from libraries
import datetime
import logging
import time
from databricks.sdk import WorkspaceClient
import databricks.sdk.service.jobs as j
from cornflow.constants import *
from cornflow.shared.const import (
    AIRFLOW_BACKEND,
    DATABRICKS_BACKEND,
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
)
# TODO AGA: Modificar import para sacarlo de cornflow_client
from cornflow.shared.databricks import Databricks
from cornflow_client.constants import INSTANCE_SCHEMA, CONFIG_SCHEMA, SOLUTION_SCHEMA
from cornflow_client.airflow.api import Airflow
# TODO AGA: Porqué el import no funcina correctamente 
from flask import request, current_app
from flask_apispec import marshal_with, use_kwargs, doc

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import InstanceModel, DeployedOrch, ExecutionModel
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
    ExecutionDetailsWithIndicatorsAndLogResponse
)
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.compress import compressed
from cornflow.shared.const import (
    EXEC_STATE_RUNNING,
    EXEC_STATE_ERROR,
    EXEC_STATE_ERROR_START,
    EXEC_STATE_NOT_RUN,
    EXEC_STATE_UNKNOWN,
    EXECUTION_STATE_MESSAGE_DICT,
    AIRFLOW_TO_STATE_MAP,
    DATABRICKS_TO_STATE_MAP,
    DATABRICKS_FINISH_TO_STATE_MAP,
    EXEC_STATE_STOPPED,
    EXEC_STATE_QUEUED,
)
from cornflow.shared.exceptions import AirflowError, DatabricksError, ObjectDoesNotExist, InvalidData
from cornflow.shared.validators import (
    json_schema_validate_as_string,
    json_schema_extend_and_validate_as_string,
)
from cornflow.orchestrator_constants import config_orchestrator


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
            dag_run_id = execution.dag_run_id
            if not dag_run_id:
                # it's safe to say we will never get anything if we did not store the dag_run_id
                current_app.logger.warning(
                    "Error while the app tried to update the status of all running executions."
                    f"Execution {execution.id} has status {execution.state} but has no dag run associated."
                )
                continue

            af_client = Airflow.from_config(current_app.config)
            if not af_client.is_alive():
                current_app.logger.warning(
                    "Error while the app tried to update the status of all running executions."
                    "Airflow is not accessible."
                )
                continue

            try:
                response = af_client.get_run_status(
                    dag_name=execution.schema, dag_run_id=dag_run_id
                )
            except AirflowError as err:
                current_app.logger.warning(
                    "Error while the app tried to update the status of all running executions."
                    f"Airflow responded with an error: {err}"
                )
                continue

            data = response.json()
            state = AIRFLOW_TO_STATE_MAP.get(data["state"], EXEC_STATE_UNKNOWN)
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
        # TODO: should validation should be done even if the execution is not going to be run?
        # TODO: should the schema field be cross validated with the instance schema field?

        ORQ_TYPE = current_app.config["CORNFLOW_BACKEND"]
        if ORQ_TYPE==AIRFLOW_BACKEND:
            orq_const= config_orchestrator["airflow"]
            ORQ_ERROR=AirflowError
        elif ORQ_TYPE==DATABRICKS_BACKEND:
            orq_const= config_orchestrator["databricks"]
            # TODO AGA: Revisar si esto funcionaría correctamente
            ORQ_ERROR=DatabricksError

        if "schema" not in kwargs:
            kwargs["schema"] = orq_const["def_schema"]
        # region INDEPENDIENTE A AIRFLOW
        config = current_app.config
        execution, status_code = self.post_list(data=kwargs)
        instance = InstanceModel.get_one_object(
            user=self.get_user(), idx=execution.instance_id
        )

        current_app.logger.debug(f"The request is: {request.args.get('run')}")
        # this allows testing without  orchestrator interaction:
        if request.args.get("run", "1") == "0":
            current_app.logger.info(
                f"User {self.get_user_id()} creates execution {execution.id} but does not run it."
            )
            execution.update_state(EXEC_STATE_NOT_RUN)
            return execution, 201

        # We now try to launch the task in the orchestrator
        # We try to create an orch client
        # Note schema is a string with the name of the job/dag
        schema = execution.schema
        # If we are dealing with DataBricks, the schema will 
        #   be the job id
        orch_client, schema_info, execution= get_orch_client(schema,ORQ_TYPE,execution)
        # endregion

        # region VALIDACIONES
        # We check if the job/dag exists 
        orch_client.get_orch_info(schema)
        # Validate config before running the dag
        config_schema = DeployedOrch.get_one_schema(config, schema, CONFIG_SCHEMA)
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
        instance_schema = DeployedOrch.get_one_schema(config, schema, INSTANCE_SCHEMA)
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
            solution_schema = DeployedOrch.get_one_schema(
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
        
        if ORQ_TYPE==AIRFLOW_BACKEND:
            info = schema_info.json()
            if info["is_paused"]:
                err = "The dag exists but it is paused in airflow"
                current_app.logger.error(err)
                execution.update_state(EXEC_STATE_ERROR_START)
                raise ORQ_ERROR(
                    error=err,
                    payload=dict(
                        message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                        state=EXEC_STATE_ERROR_START,
                    ),
                    log_txt=f"Error while user {self.get_user()} tries to create an execution. "
                    + err,
                )
        # TODO AGA: revisar si hay que hacer alguna verificación a los JOBS

        try:
            # TODO AGA: Hay que genestionar la posible eliminación de execution.id como 
            #   parámetro, ya que no se puede seleccionar el id en databricks
            #   revisar las consecuencias que puede tener
            response = orch_client.run_workflow(execution.id, orch_name=schema)
        except ORQ_ERROR as err:
            error = orq_const["name"] + " responded with an error: {}".format(err)
            current_app.logger.error(error)
            execution.update_state(EXEC_STATE_ERROR)
            raise ORQ_ERROR(
                error=error,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                    state=EXEC_STATE_ERROR,
                ),
                log_txt=f"Error while user {self.get_user()} tries to create an execution. "
                + error,
            )

        # if we succeed, we register the dag_run_id in the execution table:
        orq_data = response.json()
        # TODO AGA: revisar el nombre del modelo de ejecuciones
        execution.dag_run_id = orq_data[orq_const["run_id"]]
        execution.update_state(EXEC_STATE_QUEUED)
        current_app.logger.info(
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
        ORQ_TYPE = current_app.config["CORNFLOW_BACKEND"]
        if ORQ_TYPE==AIRFLOW_BACKEND:
            orq_const= config_orchestrator["airflow"]
            ORQ_ERROR=AirflowError
        elif ORQ_TYPE==DATABRICKS_BACKEND:
            orq_const= config_orchestrator["databricks"]
            # TODO AGA: Revisar si esto funcionaría correctamente
            ORQ_ERROR=DatabricksError

        config = current_app.config
        if "schema" not in kwargs:
            kwargs["schema"] = orq_const["def_schema"]

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
        config_schema = DeployedOrch.get_one_schema(
            config, kwargs["schema"], CONFIG_SCHEMA
        )
        config_errors = json_schema_validate_as_string(config_schema, kwargs["config"])
        if config_errors:
            raise InvalidData(
                payload=dict(jsonschema_errors=config_errors),
                log_txt=f"Error while user {self.get_user()} tries to relaunch execution {idx}. "
                f"Configuration data does not match the jsonschema.",
            )
        orch_client, schema_info, execution = get_orch_client(schema,ORQ_TYPE,execution)
        
        if not orch_client.is_alive():
            err = orq_const["name"]+" is not accessible"
            current_app.logger.error(err)
            execution.update_state(EXEC_STATE_ERROR_START)
            raise ORQ_ERROR(
                error=err,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                    state=EXEC_STATE_ERROR_START,
                ),
                log_txt=f"Error while user {self.get_user()} tries to relaunch execution {idx}. "
                + err,
            )
        
        # ask airflow if dag_name exists
        schema = execution.schema
        schema_info = orch_client.get_orch_info(schema)

        info = schema_info.json()
        if ORQ_TYPE==AIRFLOW_BACKEND:
            if info["is_paused"]:
                err = "The dag exists but it is paused in airflow"
                current_app.logger.error(err)
                execution.update_state(EXEC_STATE_ERROR_START)
                raise ORQ_ERROR(
                    error=err,
                    payload=dict(
                        message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                        state=EXEC_STATE_ERROR_START,
                    ),
                    log_txt=f"Error while user {self.get_user()} tries to relaunch execution {idx}. "
                    + err,
                )
        # TODO AGA: revisar si hay que hacer alguna comprobación del estilo a databricks
        try:
            response = orch_client.run_workflow(execution.id, orch_name=schema)
        except ORQ_ERROR as err:
            error = orq_const["name"]+" responded with an error: {}".format(err)
            current_app.logger.error(error)
            execution.update_state(EXEC_STATE_ERROR)
            raise ORQ_ERROR(
                error=error,
                payload=dict(
                    message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR],
                    state=EXEC_STATE_ERROR,
                ),
                log_txt=f"Error while user {self.get_user()} tries to relaunch execution {idx}. "
                + error,
            )

        # if we succeed, we register the dag_run_id in the execution table:
        orq_data = response.json()
        # TODO AGA: revisar el nombre del modelo de ejecuciones
        execution.dag_run_id = orq_data[orq_const["run_id"]]
        execution.update_state(EXEC_STATE_QUEUED)
        current_app.logger.info(
            "User {} relaunches execution {}".format(self.get_user_id(), execution.id)
        )
        return {"message": "The execution was relaunched correctly"}, 201


class ExecutionDetailsEndpointBase(BaseMetaResource):
    """
    Endpoint used to get the information of a certain execution. But not the data!
    """
    # TODO AGA DUDA: Se usa? Qué debería devolver?
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
            data_jsonschema = DeployedOrch.get_one_schema(
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
        execution = ExecutionModel.get_one_object(user=self.get_user(), idx=idx)
        if execution is None:
            raise ObjectDoesNotExist(
                log_txt=f"Error while user {self.get_user()} tries to stop execution {idx}. "
                f"The execution does not exist."
            )
        af_client = Airflow.from_config(current_app.config)
        if not af_client.is_alive():
            err = "Airflow is not accessible"
            raise AirflowError(
                error=err,
                log_txt=f"Error while user {self.get_user()} tries to stop execution {idx}. "
                + err,
            )
        response = af_client.set_dag_run_to_fail(
            dag_name=execution.schema, dag_run_id=execution.dag_run_id
        )
        execution.update_state(EXEC_STATE_STOPPED)
        current_app.logger.info(f"User {self.get_user()} stopped execution {idx}")
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
        ORQ_TYPE = current_app.config["CORNFLOW_BACKEND"]
        if ORQ_TYPE==AIRFLOW_BACKEND:
            orq_const= config_orchestrator["airflow"]
            ORQ_ERROR=AirflowError
        elif ORQ_TYPE==DATABRICKS_BACKEND:
            orq_const= config_orchestrator["databricks"]
            # TODO AGA: Revisar si esto funcionaría correctamente
            ORQ_ERROR=DatabricksError
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
            raise ORQ_ERROR(
                error=error, payload=dict(message=message, state=state), log_txt=log_txt
            )

        dag_run_id = execution.dag_run_id
        if not dag_run_id:
            # it's safe to say we will never get anything if we did not store the dag_run_id
            _raise_af_error(
                execution,
                state=EXEC_STATE_ERROR,
                error="The execution has no dag_run associated",
                log_txt=f"Error while user {self.get_user()} tries to get the status of execution {idx}. "
                f"The execution has no associated dag run id.",
            )
        schema = execution.schema
        # TODO AGA: Revisar si merece la pena hacer una funcion que solo
        orch_client, schema_info, execution= get_orch_client(schema ,ORQ_TYPE,execution)

        if not orch_client.is_alive():
            err = orq_const["name"] +" is not accessible"
            _raise_af_error(
                execution,
                err,
                log_txt=f"Error while user {self.get_user()} tries to get the status of execution {idx}. "
                + err,
            )

        try:
            # TODO: get the dag_name from somewhere!
            state = orch_client.get_run_status(
                dag_name=execution.schema, dag_run_id=dag_run_id
            )
        except ORQ_ERROR as err:
            error = orq_const["name"] +f" responded with an error: {err}"
            _raise_af_error(
                execution,
                error,
                log_txt=f"Error while user {self.get_user()} tries to get the status of execution {idx}. "
                + str(err),
            )

        state = map_run_state(state, ORQ_TYPE)
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
def submit_one_job(cid):
    # trigger one-time-run job and get waiter object
    waiter = w.jobs.submit(run_name=f'cornflow-job-{time.time()}', tasks=[
        j.SubmitTask(
            task_key='nippon_production_scheduling',
            existing_cluster_id=cid,
            libraries=[],
            spark_python_task=j.SparkPythonTask(
                python_file='/Workspace/Repos/nippon/nippon_production_scheduling/main.py',
            ),
            timeout_seconds=0,
        )
    ])
    logging.info(f'starting to poll: {waiter.run_id}')
    # callback, that receives a polled entity between state updates
    # If you want to perform polling in a separate thread, process, or service,
    # you can use w.jobs.wait_get_run_job_terminated_or_skipped(
    #   run_id=waiter.run_id,
    #   timeout=datetime.timedelta(minutes=15),
    #   callback=print_status) to achieve the same results.
    #
    # Waiter interface allows for `w.jobs.submit(..).result()` simplicity in
    # the scenarios, where you need to block the calling thread for the job to finish.
    run = waiter.result(timeout=datetime.timedelta(minutes=15),
                        callback=print_status)
    logging.info(f'job finished: {run.run_page_url}')
    return waiter.run_id

def print_status(run: j.Run):
    statuses = [f'{t.task_key}: {t.state.life_cycle_state}' for t in run.tasks]
    logging.info(f'workflow intermediate status: {", ".join(statuses)}')

def get_orch_client(schema, orq_type, execution):
    """
    Get the orchestrator client and the schema info
    """
    if orq_type == AIRFLOW_BACKEND:
        return get_airflow(schema, execution=execution)
    elif orq_type == DATABRICKS_BACKEND:
        return get_databricks(schema,execution=execution)
    else:
        raise EndpointNotImplemented()
            

def get_airflow(schema, execution):
    """
    Get the Airflow client and the schema info
    """
    af_client = Airflow.from_config(current_app.config)
    schema_info = af_client.get_orch_info(schema)
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
            log_txt=f"Error while user {self.get_user()} tries to create an execution "
            + err,
        )
    # TODO AGA: revisar si tiene sentido que se devuelva execution o si 
    #  es un puntero
    return af_client,schema_info, execution


def get_databricks(schema, execution):
    """
    Get the Databricks client and the schema info
    """
    db_client = Databricks.from_config(current_app.config)
    schema_info = db_client.get_orch_info
    if not db_client.is_alive():
        err = "Databricks is not accessible"
        current_app.logger.error(err)
        execution.update_state(EXEC_STATE_ERROR_START)
        raise DatabricksError(
            error=err,
            payload=dict(
                message=EXECUTION_STATE_MESSAGE_DICT[EXEC_STATE_ERROR_START],
                state=EXEC_STATE_ERROR_START,
            ),
            log_txt=f"Error while user {self.get_user()} tries to create an execution "
            + err,
        )
    return db_client, schema_info, execution
    # endregion

def map_run_state(state,ORQ_TYPE):
    """
    Maps the state of the execution in the orchestrator to the state of the execution in cornflow
    """
    if ORQ_TYPE==AIRFLOW_BACKEND:
        return AIRFLOW_TO_STATE_MAP.get(state, EXEC_STATE_UNKNOWN)
    elif ORQ_TYPE==DATABRICKS_BACKEND:
        preliminar_state = DATABRICKS_TO_STATE_MAP.get(state,EXEC_STATE_UNKNOWN)
        if preliminar_state =="TERMINATED":
            # TODO AGA DUDA: Revisar si es correcto el error predeterminado
            return DATABRICKS_FINISH_TO_STATE_MAP.get(state,EXEC_STATE_ERROR)
        return preliminar_state
