"""
Internal endpoint for getting and posting execution data
This are the endpoints used by airflow in its communication with cornflow
"""
# Import from libraries
from flask_restful import Resource
from flask_apispec import use_kwargs, doc
from flask_apispec.views import MethodResource

# Import from internal modules
from ..models import ExecutionModel, InstanceModel
from ..schemas import ExecutionSchema
from ..shared.authentication import Auth
from ..shared.const import EXEC_STATE_CORRECT, EXECUTION_STATE_MESSAGE_DICT
from ..schemas.execution import ExecutionDagRequest
from ..shared.exceptions import ObjectDoesNotExist, InvalidUsage
from ..schemas.model_json import DataSchema
from ..schemas.schema_manager import SchemaManager
from json_schemas import get_path

execution_schema = ExecutionSchema()


class DAGEndpoint(Resource, MethodResource):
    """
    Endpoint used for the DAG endpoint
    """

    @doc(description='Add a solution to an execution', tags=['DAGs'])
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
        state = req_data.get('state', EXEC_STATE_CORRECT)
        solution_schema = req_data.get('solution_schema', "pulp")
        
        # Check data fromat
        if solution_schema == 'pulp':
            validate = DataSchema().load(req_data['execution_results'])
            err = ''
            if validate is None:
                raise InvalidUsage(error='Bad instance data format: {}'.format(err))
        else:
            schema_path = get_path(solution_schema)
    
            if not schema_path:
                raise InvalidUsage(error='Bad data schema name: this data schema does not exist')
    
            manager = SchemaManager.from_filepath(schema_path)
            err = manager.get_validation_errors(req_data['execution_results'])
            if err:
                raise InvalidUsage(error='Bad solution data format: {}'.format(err))
        
        execution = ExecutionModel.get_one_execution_from_id_admin(idx)
        if execution is None:
            raise ObjectDoesNotExist()
        new_data = \
            dict(
                finished=True,
                state=state,
                state_message=EXECUTION_STATE_MESSAGE_DICT[state],
                # because we do not want to store airflow's user:
                user_id = execution.user_id
             )
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
        execution = ExecutionModel.get_one_execution_from_id_admin(idx)
        if execution is None:
            raise ObjectDoesNotExist(error='The execution does not exist')
        instance = InstanceModel.get_one_instance_from_id_admin(execution.instance_id)
        if instance is None:
            raise ObjectDoesNotExist(error='The instance does not exist')
        config = execution.config
        return {"data": instance.data, "config": config}, 200
