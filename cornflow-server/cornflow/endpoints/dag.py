"""
Internal endpoint for getting and posting execution data
These are the endpoints used by airflow in its communication with cornflow
"""

# Import from libraries
from cornflow_client.constants import SOLUTION_SCHEMA
from flask import current_app
from flask_apispec import use_kwargs, doc, marshal_with

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import DeployedDAG, ExecutionModel, InstanceModel, CaseModel
from cornflow.schemas import DeployedDAGSchema, DeployedDAGEditSchema
from cornflow.schemas.case import CaseCheckRequest
from cornflow.schemas.instance import InstanceCheckRequest
from cornflow.schemas.execution import (
    ExecutionDagPostRequest,
    ExecutionDagRequest,
    ExecutionDetailsEndpointResponse,
)

from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import (
    ADMIN_ROLE,
    EXEC_STATE_CORRECT,
    EXEC_STATE_MANUAL,
    EXECUTION_STATE_MESSAGE_DICT,
    SERVICE_ROLE,
    PLANNER_ROLE,
)
from cornflow.shared.exceptions import ObjectDoesNotExist, InvalidData
from cornflow.shared.validators import json_schema_validate_as_string


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
            err = "The execution does not exist."
            raise ObjectDoesNotExist(
                error=err,
                log_txt=f"Error while user {self.get_user()} tries to get input data for execution {idx}."
                + err,
            )
        instance = InstanceModel.get_one_object(
            user=self.get_user(), idx=execution.instance_id
        )
        if instance is None:
            err = "The instance does not exist."
            raise ObjectDoesNotExist(
                error=err,
                log_txt=f"Error while user {self.get_user()} tries to get input data for execution {idx}."
                + err,
            )
        config = execution.config
        current_app.logger.info(
            f"User {self.get_user()} gets input data of execution {idx}"
        )
        return {
            "id": instance.id,
            "data": instance.data,
            "solution_data": execution.data,
            "config": config,
        }, 200

    @doc(description="Edit an execution", tags=["DAGs"])
    @authenticate(auth_class=Auth())
    @use_kwargs(ExecutionDagRequest, location="json")
    def put(self, idx, **kwargs):
        """
        API method to write the results of the execution
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by the superuser created for the airflow webserver

        :param str idx: ID of the execution
        :return: A dictionary with a message (body) and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        execution = ExecutionModel.get_one_object(user=self.get_user(), idx=idx)
        if execution is None:
            err = "The execution does not exist."
            raise ObjectDoesNotExist(
                error=err,
                log_txt=f"Error while user {self.get_user()} tries to edit execution {idx}."
                + err,
            )

        solution_schema = execution.schema

        # Check data format
        data = kwargs.get("data")
        checks = kwargs.get("checks")
        if data is None:
            # only check format if executions_results exist
            solution_schema = None
        if solution_schema == "pulp":
            # The dag name is solve_model_dag
            solution_schema = "solve_model_dag"
        if solution_schema is not None:
            config = current_app.config

            solution_schema = DeployedDAG.get_one_schema(
                config, solution_schema, SOLUTION_SCHEMA
            )
            solution_errors = json_schema_validate_as_string(solution_schema, data)

            if solution_errors:
                raise InvalidData(
                    payload=dict(jsonschema_errors=solution_errors),
                    log_txt=f"Error while user {self.get_user()} tries to edit execution {idx}. "
                    f"Solution data do not match the jsonschema.",
                )

        state = kwargs.get("state", EXEC_STATE_CORRECT)
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
        kwargs.update(new_data)
        execution.update(kwargs)

        current_app.logger.info(f"User {self.get_user()} edits execution {idx}")
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
        current_app.logger.info(f"Instance checks saved for instance {idx}")
        return self.put_detail(data=req_data, idx=idx, track_user=False)


class DAGCaseEndpoint(BaseMetaResource):
    """
    Endpoint used by airflow to write case checks
    """

    ROLES_WITH_ACCESS = [ADMIN_ROLE, SERVICE_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = CaseModel

    @doc(
        description="Endpoint to save case checks performed on the DAG",
        tags=["DAGs"],
    )
    @authenticate(auth_class=Auth())
    @use_kwargs(CaseCheckRequest, location="json")
    def put(self, idx, **req_data):
        current_app.logger.info(f"Case checks saved for instance {idx}")
        return self.put_detail(data=req_data, idx=idx, track_user=False)


class DAGEndpointManual(BaseMetaResource):
    """ """

    ROLES_WITH_ACCESS = [PLANNER_ROLE, ADMIN_ROLE, SERVICE_ROLE]

    @doc(description="Create an execution manually.", tags=["DAGs"])
    @authenticate(auth_class=Auth())
    @marshal_with(ExecutionDetailsEndpointResponse)
    @use_kwargs(ExecutionDagPostRequest, location="json")
    def post(self, **kwargs):
        solution_schema = kwargs.pop("dag_name", None)

        # Check data format
        data = kwargs.get("data")
        if data is None:
            # only check format if executions_results exist
            solution_schema = None
        if solution_schema == "pulp":
            solution_schema = "solve_model_dag"
        if solution_schema is not None:
            config = current_app.config
            solution_schema = DeployedDAG.get_one_schema(
                config, solution_schema, SOLUTION_SCHEMA
            )
            solution_errors = json_schema_validate_as_string(solution_schema, data)

            if solution_errors:
                raise InvalidData(
                    payload=dict(jsonschema_errors=solution_errors),
                    log_txt=f"Error while user {self.get_user()} tries to manually create an execution. "
                    f"Solution data do not match the jsonschema.",
                )

        kwargs_copy = dict(kwargs)
        # we force the state to manual
        kwargs_copy["state"] = EXEC_STATE_MANUAL
        kwargs_copy["user_id"] = self.get_user_id()
        if data is not None:
            kwargs_copy["data"] = data
        item = ExecutionModel(kwargs_copy)
        item.save()
        current_app.logger.info(
            f"User {self.get_user()} manually created the execution {item.id}"
        )
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


class DeployedDagDetailEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [SERVICE_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = DeployedDAG

    @doc(
        description="Endpoint to update the schemas of a deployed DAG",
        tags=["DAGs"],
    )
    @authenticate(auth_class=Auth())
    @use_kwargs(DeployedDAGEditSchema, location="json")
    def put(self, idx, **req_data):
        current_app.logger.info(f"Schemas saved for DAG {idx}")
        return self.put_detail(data=req_data, idx=idx, track_user=False)
