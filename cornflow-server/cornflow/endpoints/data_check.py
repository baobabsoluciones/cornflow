"""
External endpoints to launch the solution check on an execution
"""

# Import from libraries
from cornflow_client.airflow.api import Airflow
from cornflow_core.resources import BaseMetaResource
from flask import request, current_app
from flask_apispec import marshal_with, use_kwargs, doc
import logging as log

# Import from internal modules
from ..models import InstanceModel, ExecutionModel
from ..schemas.execution import (
    ExecutionDetailsEndpointResponse,
    QueryFiltersExecution,
)
from ..schemas.data_check import (
    DataCheckRequest,
)

from ..shared.authentication import Auth
from ..shared.const import (
    EXEC_STATE_RUNNING,
    EXEC_STATE_ERROR,
    EXEC_STATE_ERROR_START,
    EXEC_STATE_NOT_RUN,
    EXECUTION_STATE_MESSAGE_DICT,
    SERVICE_ROLE,
    ADMIN_ROLE,
)
from cornflow_core.authentication import authenticate
from cornflow_core.exceptions import AirflowError, ObjectDoesNotExist


class DataCheckEndpoint(BaseMetaResource):
    """
    Endpoint used to execute the instance and solution checks on an execution
    """
    ROLES_WITH_ACCESS = [ADMIN_ROLE, SERVICE_ROLE]

    def __init__(self):
        super().__init__()
        self.model = ExecutionModel
        self.data_model = ExecutionModel
        self.foreign_data = {"instance_id": InstanceModel}

    """    @doc(description="Get all executions", tags=["Executions"])
    @authenticate(auth_class=Auth())
    @marshal_with(ExecutionDetailsEndpointResponse(many=True))
    @use_kwargs(QueryFiltersExecution, location="query")
    def get(self, **kwargs):
        "" "
        API method to get all the executions created by the user and its related info
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed or a list with all the executions
          created by the authenticated user) and a integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        "" "
        return self.get_list(user=self.get_user(), **kwargs)"""

    @doc(description="Create a data check execution", tags=["Data checks"])
    @authenticate(auth_class=Auth())
    @Auth.dag_permission_required
    @marshal_with(ExecutionDetailsEndpointResponse)
    @use_kwargs(DataCheckRequest, location="json")
    def post(self, **kwargs):
        """
        API method to create a new data check linked to an already existing execution
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: A dictionary with a message (error if authentication failed, error if data is not validated or
          the reference_id for the newly created execution if successful) and a integer wit the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        config = current_app.config

        exec_to_check = ExecutionModel.get_one_object(
            user=self.get_user(), idx=kwargs["execution_id"]
        )
        if exec_to_check is None:
            raise ObjectDoesNotExist(error="The execution to solve does not exist")
        kwargs["instance_id"] = exec_to_check.instance_id
        kwargs["config"]["checks_only"] = True
        kwargs["config"]["execution_id"] = kwargs.pop("execution_id")
        kwargs["config"]["schema"] = exec_to_check.schema
        schema = exec_to_check.schema

        execution, status_code = self.post_list(data=kwargs)

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
            response = af_client.run_dag(execution.id, dag_name=schema, checks_only=True)
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
