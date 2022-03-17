"""
External endpoints to manage the executions: create new ones, list all of them, get one in particular
or check the status of an ongoing one
These endpoints hve different access url, but manage the same data entities
"""

# Import from libraries
from cornflow_client.airflow.api import Airflow, get_schema, validate_and_continue
from cornflow_client.constants import INSTANCE_SCHEMA
from flask import request, current_app
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, use_kwargs, doc
import logging as log

# Import from internal modules
from .meta_resource import MetaResource
from ..models import InstanceModel, ExecutionModel
from ..schemas.execution import (
    ExecutionSchema,
    ExecutionDetailsEndpointResponse,
    ExecutionDataEndpointResponse,
    ExecutionLogEndpointResponse,
    ExecutionStatusEndpointResponse,
    ExecutionRequest,
    ExecutionEditRequest,
    QueryFiltersExecution,
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
)

from ..shared.exceptions import AirflowError, ObjectDoesNotExist
from ..shared.compress import compressed


# Initialize the schema that all endpoints are going to use
# TODO: is it needed?
execution_schema = ExecutionSchema()


class ExecutionEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to create a new execution or get all the executions and their information back
    """

    def __init__(self):
        super().__init__()
        self.model = ExecutionModel
        self.query = ExecutionModel.get_all_objects
        self.primary_key = "id"
        self.foreign_data = {"instance_id": InstanceModel}

    @doc(description="Get all executions", tags=["Executions"])
    @Auth.auth_required
    @marshal_with(ExecutionDetailsEndpointResponse(many=True))
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
        return ExecutionModel.get_all_objects(self.get_user(), **kwargs)

    @doc(description="Create an execution", tags=["Executions"])
    @Auth.auth_required
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
        # TODO: should the schema field be cross valdiated with the instance schema field?
        config = current_app.config

        if "schema" not in kwargs:
            kwargs["schema"] = "solve_model_dag"
        execution, status_code = self.post_list(kwargs)
        instance = InstanceModel.get_one_object_from_user(
            self.get_user(), execution.instance_id
        )

        if instance is None:
            raise ObjectDoesNotExist(error="The instance to solve does not exist")

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

        # Validate that instance and dag_name are compatible
        marshmallow_obj = get_schema(config, schema, INSTANCE_SCHEMA)
        validate_and_continue(marshmallow_obj(), instance.data)

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
        execution.update_state(EXEC_STATE_RUNNING)
        log.info(
            "User {} creates execution {}".format(self.get_user_id(), execution.id)
        )
        return execution, 201


class ExecutionDetailsEndpointBase(MetaResource, MethodResource):
    """
    Endpoint used to get the information of a certain execution. But not the data!
    """

    def __init__(self):
        super().__init__()
        self.model = ExecutionModel
        self.query = ExecutionModel.get_one_object_from_user
        self.primary_key = "id"
        self.foreign_data = {"instance_id": InstanceModel}


class ExecutionDetailsEndpoint(ExecutionDetailsEndpointBase):
    @doc(description="Get details of an execution", tags=["Executions"], inherit=False)
    @Auth.auth_required
    @marshal_with(ExecutionDetailsEndpointResponse)
    @MetaResource.get_data_or_404
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
        return ExecutionModel.get_one_object_from_user(user=self.get_user(), idx=idx)

    @doc(description="Edit an execution", tags=["Executions"], inherit=False)
    @Auth.auth_required
    @use_kwargs(ExecutionEditRequest, location="json")
    def put(self, idx, **data):
        """
        Edit an existing execution

        :param string idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        log.info(f"User {self.get_user_id()} edits execution {idx}")
        return self.put_detail(data, self.get_user(), idx)

    @doc(description="Delete an execution", tags=["Executions"], inherit=False)
    @Auth.auth_required
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
        log.info(f"User {self.get_user_id()} deleted execution {idx}")
        return self.delete_detail(self.get_user(), idx)

    @doc(description="Stop an execution", tags=["Executions"], inherit=False)
    @Auth.auth_required
    @Auth.dag_permission_required
    def post(self, idx):
        execution = ExecutionModel.get_one_object_from_user(
            user=self.get_user(), idx=idx
        )
        if execution is None:
            raise ObjectDoesNotExist()
        af_client = Airflow.from_config(current_app.config)
        if not af_client.is_alive():
            raise AirflowError(error="Airflow is not accessible")
        response = af_client.set_dag_run_to_fail(
            dag_name=execution.schema, dag_run_id=execution.dag_run_id
        )
        execution.update_state(EXEC_STATE_STOPPED)
        log.info(f"User {self.get_user_id()} stopped execution {idx}")
        return {"message": "The execution has been stopped"}, 200


class ExecutionStatusEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to get the status of a certain execution that is running in the airflow webserver
    """

    @doc(description="Get status of an execution", tags=["Executions"])
    @Auth.auth_required
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
        execution = ExecutionModel.get_one_object_from_user(
            user=self.get_user(), idx=idx
        )
        if execution is None:
            raise ObjectDoesNotExist()
        if execution.state not in [EXEC_STATE_RUNNING, EXEC_STATE_UNKNOWN]:
            # we only care on asking airflow if the status is unknown or is running.
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
            _raise_af_error(
                execution, f"Airflow responded with an error: {err}"
            )

        data = response.json()
        state = AIRFLOW_TO_STATE_MAP.get(data["state"], EXEC_STATE_UNKNOWN)
        execution.update_state(state)
        return execution, 200


class ExecutionDataEndpoint(ExecutionDetailsEndpointBase):
    """
    Endpoint used to get the solution of a certain execution.
    """

    @doc(
        description="Get solution data of an execution",
        tags=["Executions"],
        inherit=False,
    )
    @Auth.auth_required
    @marshal_with(ExecutionDataEndpointResponse)
    @MetaResource.get_data_or_404
    @compressed
    def get(self, idx):
        """

        :param str idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the execution) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return ExecutionModel.get_one_object_from_user(user=self.get_user(), idx=idx)


class ExecutionLogEndpoint(ExecutionDetailsEndpointBase):
    """
    Endpoint used to get the log of a certain execution.
    """

    @doc(description="Get log of an execution", tags=["Executions"], inherit=False)
    @Auth.auth_required
    @marshal_with(ExecutionLogEndpointResponse)
    @MetaResource.get_data_or_404
    @compressed
    def get(self, idx):
        """

        :param str idx: ID of the execution.
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          the data of the execution) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return ExecutionModel.get_one_object_from_user(user=self.get_user(), idx=idx)
