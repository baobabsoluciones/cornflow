"""
Internal endpoint for getting and posting execution data
This are the endpoints used by airflow in its communication with cornflow
"""
# Import from libraries
from cornflow_client.airflow.api import get_schema
from cornflow_core.shared import validate_and_continue
from cornflow_client.constants import SOLUTION_SCHEMA
from flask import current_app
from flask_apispec import use_kwargs, doc, marshal_with
import logging as log

# Import from internal modules
from ..models import DeployedDAG, ExecutionModel, InstanceModel
from ..schemas import DeployedDAGSchema
from ..schemas.instance import InstanceCheckRequest
from ..schemas.execution import (
    ExecutionDagPostRequest,
    ExecutionDagRequest,
    ExecutionDetailsEndpointResponse,
    ExecutionSchema,
)

from ..schemas.model_json import DataSchema
from ..shared.authentication import Auth
from ..shared.const import (
    ADMIN_ROLE,
    EXEC_STATE_CORRECT,
    EXEC_STATE_MANUAL,
    EXECUTION_STATE_MESSAGE_DICT,
    SERVICE_ROLE,
)

from cornflow_core.exceptions import ObjectDoesNotExist
from cornflow_core.authentication import authenticate
from cornflow_core.resources import BaseMetaResource

execution_schema = ExecutionSchema()


class DAGDetailEndpoint(BaseMetaResource):
    """
    Endpoint used for the DAG endpoint
    """

    ROLES_WITH_ACCESS = [ADMIN_ROLE, SERVICE_ROLE]

    @doc(description="Get input data and configuration for an execution", tags=["DAGs"])
    @authenticate(auth_class=Auth())
    def get(self, idx):
        """
        API method to get the data of the instance that is going to be executed
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by the superuser created for the airflow webserver

        :param str idx: ID of the execution
        :return: the execution data (body) in a dictionary with structure of :class:`ConfigSchema`
          and :class:`DataSchema` and an integer for HTTP status code
        :rtype: Tuple(dict, integer)
        """
        execution = ExecutionModel.get_one_object(user=self.get_user(), idx=idx)
        if execution is None:
            raise ObjectDoesNotExist(error="The execution does not exist")
        instance = InstanceModel.get_one_object(
            user=self.get_user(), idx=execution.instance_id
        )
        if instance is None:
            raise ObjectDoesNotExist(error="The instance does not exist")
        config = execution.config
        return {"id": instance.id, "data": instance.data, "config": config}, 200

    @doc(description="Edit an execution", tags=["DAGs"])
    @authenticate(auth_class=Auth())
    @use_kwargs(ExecutionDagRequest, location="json")
    def put(self, idx, **req_data):
        """
        API method to write the results of the execution
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by the superuser created for the airflow webserver

        :param str idx: ID of the execution
        :return: A dictionary with a message (body) and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        solution_schema = req_data.pop("solution_schema", "pulp")
        # TODO: the solution_schema maybe we should get it from the created execution_id?
        #  at least, check they have the same schema-name
        # Check data format
        data = req_data.get("data")
        checks = req_data.get("checks")
        if data is None:
            # only check format if executions_results exist
            solution_schema = None
        if solution_schema == "pulp":
            validate_and_continue(DataSchema(), data)
        elif solution_schema is not None:
            config = current_app.config
            marshmallow_obj = get_schema(config, solution_schema, SOLUTION_SCHEMA)
            validate_and_continue(marshmallow_obj(), data)
            # marshmallow_obj().fields['jobs'].nested().fields['successors']
        execution = ExecutionModel.get_one_object(user=self.get_user(), idx=idx)
        if execution is None:
            raise ObjectDoesNotExist()
        state = req_data.get("state", EXEC_STATE_CORRECT)
        new_data = dict(
            state=state,
            state_message=EXECUTION_STATE_MESSAGE_DICT[state],
            # because we do not want to store airflow's user:
            user_id=execution.user_id,
        )

        # newly validated data from marshmallow
        if data is not None:
            new_data["data"] = data
        if checks is not None:
            new_data["checks"] = checks
        req_data.update(new_data)
        execution.update(req_data)
        # TODO: is this save necessary?
        execution.save()
        return {"message": "results successfully saved"}, 200


class DAGInstanceEndpoint(BaseMetaResource):
    """
    Endpoint used by airflow to write instance checks
    """

    ROLES_WITH_ACCESS = [ADMIN_ROLE, SERVICE_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = InstanceModel

    @doc(
        description="Endpoint to save instance checks performed on the DAG",
        tags=["DAGs"],
    )
    @authenticate(auth_class=Auth())
    @use_kwargs(InstanceCheckRequest, location="json")
    def put(self, idx, **req_data):
        log.info(f"Instance checks saved for instance {idx}")
        return self.put_detail(data=req_data, idx=idx, track_user=False)


class DAGEndpointManual(BaseMetaResource):
    """ """

    ROLES_WITH_ACCESS = [ADMIN_ROLE, SERVICE_ROLE]

    @doc(description="Create an execution manually.", tags=["DAGs"])
    @authenticate(auth_class=Auth())
    @marshal_with(ExecutionDetailsEndpointResponse)
    @use_kwargs(ExecutionDagPostRequest, location="json")
    def post(self, **kwargs):
        solution_schema = kwargs.pop("dag_name", None)

        # Check data format
        data = kwargs.get("data")
        # TODO: create a function to validate and replace data/ execution_results
        if data is None:
            # only check format if executions_results exist
            solution_schema = None
        if solution_schema == "pulp":
            validate_and_continue(DataSchema(), data)
        elif solution_schema is not None:
            config = current_app.config
            marshmallow_obj = get_schema(config, solution_schema, SOLUTION_SCHEMA)
            validate_and_continue(marshmallow_obj(), data)

        kwargs_copy = dict(kwargs)
        # we force the state to manual
        kwargs_copy["state"] = EXEC_STATE_MANUAL
        kwargs_copy["user_id"] = self.get_user_id()
        if data is not None:
            kwargs_copy["data"] = data
        item = ExecutionModel(kwargs_copy)
        item.save()
        log.info(f"User {self.get_user()} manually created the execution {item.id}")
        return item, 201


class DeployedDAGEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [SERVICE_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = DeployedDAG

    @doc(
        description="Get list of deployed dags registered on the data base",
        tags=["DeployedDAGs"],
    )
    @authenticate(auth_class=Auth())
    @marshal_with(DeployedDAGSchema(many=True))
    def get(self):
        return self.get_list()

    @doc(description="Post a new deployed dag", tags=["DeployedDAGs"])
    @authenticate(auth_class=Auth())
    @marshal_with(DeployedDAGSchema)
    @use_kwargs(DeployedDAGSchema)
    def post(self, **kwargs):
        return self.post_list(kwargs)
