"""
Internal endpoint for getting and posting execution data
This are the endpoints used by airflow in its communication with cornflow
"""
# Import from libraries
from flask import current_app
from flask_apispec import use_kwargs, doc, marshal_with
from flask_apispec.views import MethodResource

# Import from internal modules
from .meta_resource import MetaResource
from ..models import ExecutionModel, InstanceModel
from ..schemas import ExecutionSchema
from ..shared.authentication import Auth
from ..shared.const import EXEC_STATE_CORRECT, EXECUTION_STATE_MESSAGE_DICT
from ..schemas.execution import ExecutionDagRequest, ExecutionDagPostRequest, \
    ExecutionDetailsEndpointResponse
from ..shared.exceptions import ObjectDoesNotExist, InvalidUsage
from cornflow_client.airflow.api import get_schema, validate_and_continue
from cornflow_client.constants import INSTANCE_SCHEMA, SOLUTION_SCHEMA
from ..shared.const import EXEC_STATE_MANUAL
from ..schemas.model_json import DataSchema


execution_schema = ExecutionSchema()


class DAGEndpoint(MetaResource, MethodResource):
    """
    Endpoint used for the DAG endpoint
    """

    @doc(description='Edit an execution', tags=['DAGs'])
    @Auth.super_admin_required
    @use_kwargs(ExecutionDagRequest, location='json')
    def put(self, idx, **req_data):
        """
        API method to write the results of the execution
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by the superuser created for the airflow webserver

        :param str idx: ID of the execution
        :return: A dictionary with a message (body) and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        solution_schema = req_data.pop('solution_schema', "pulp")

        # Check data format
        data = req_data.get('execution_results')
        if data is None:
            # only check format if executions_results exist
            solution_schema = None
        if solution_schema == 'pulp':
            validate_and_continue(DataSchema(), data)
        elif solution_schema is not None:
            config = current_app.config
            marshmallow_obj = get_schema(config, solution_schema, SOLUTION_SCHEMA)
            validate_and_continue(marshmallow_obj(), data)
            # marshmallow_obj().fields['jobs'].nested().fields['successors']
        execution = ExecutionModel.get_one_object_from_user(self.get_user(), idx)
        if execution is None:
            raise ObjectDoesNotExist()
        state = req_data.get('state', EXEC_STATE_CORRECT)
        new_data = \
            dict(
                finished=True,
                state=state,
                state_message=EXECUTION_STATE_MESSAGE_DICT[state],
                # because we do not want to store airflow's user:
                user_id = execution.user_id
             )
        # newly validated data from marshmallow
        if data is not None:
            new_data['execution_results'] = data
        req_data.update(new_data)
        execution.update(req_data)
        execution.save()
        return {'message': 'results successfully saved'}, 201

    @doc(description='Get input data and configuration for an execution', tags=['DAGs'])
    @Auth.super_admin_required
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
        execution = ExecutionModel.get_one_object_from_user(self.get_user(), idx)
        if execution is None:
            raise ObjectDoesNotExist(error='The execution does not exist')
        instance = InstanceModel.get_one_object_from_user(self.get_user(), execution.instance_id)
        if instance is None:
            raise ObjectDoesNotExist(error='The instance does not exist')
        config = execution.config
        return {"data": instance.data, "config": config}, 200


class DAGEndpointManual(MetaResource, MethodResource):

    @doc(description='Create an execution manually.', tags=['DAGs'])
    @Auth.super_admin_required
    @marshal_with(ExecutionDetailsEndpointResponse)
    @use_kwargs(ExecutionDagPostRequest, location='json')
    def post(self, **kwargs):
        solution_schema = kwargs.pop('dag_name', None)

        # Check data format
        data = kwargs.get('execution_results')
        # TODO: create a function to validate and replace data/ execution_results
        if data is None:
            # only check format if executions_results exist
            solution_schema = None
        if solution_schema == 'pulp':
            validate_and_continue(DataSchema(), data)
        elif solution_schema is not None:
            config = current_app.config
            marshmallow_obj = get_schema(config, solution_schema, SOLUTION_SCHEMA)
            validate_and_continue(marshmallow_obj(), data)

        kwargs_copy = dict(kwargs)
        # we force the state to manual
        kwargs_copy['state'] = EXEC_STATE_MANUAL
        kwargs_copy['user_id'] = self.get_user_id()
        if data is not None:
            kwargs_copy['execution_results'] = data
        item = ExecutionModel(kwargs_copy)
        item.save()
        return item, 201
