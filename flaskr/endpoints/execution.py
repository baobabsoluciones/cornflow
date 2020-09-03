import requests

from flask import request
from flask_restful import Resource

from ..models.execution import ExecutionModel
from ..models.instance import InstanceModel
from ..schemas.execution_schema import  ExecutionSchema
from ..shared.authentication import Auth

from urllib.parse import urljoin

# TODO: AIRFLOW_URL should be modifiable
AIRFLOW_URL = "http://localhost:8080"
execution_schema = ExecutionSchema()

class ExecutionEndpoint(Resource):

    @Auth.auth_required
    def post(self):
        req_data = request.get_json()
        data = execution_schema.load(req_data, partial=True)

        data['user_id'], admin, super_admin = Auth.return_user_info(request)
        data['instance_id'] = InstanceModel.get_instance_id(data['instance'])
        instance_owner = InstanceModel.get_instance_owner(data['instance'])

        if instance_owner != data['user_id']:
            return {'error': 'You do not have permissions for the instance'}, 400

        execution = ExecutionModel(data)
        execution.save()

        ser_data = execution_schema.dump(execution)
        execution_id = ser_data.get('reference_id')
        
        # solve
        conf = "{\"exec_id\":\"%s\"}" % execution_id

        response = requests.post(
            urljoin(AIRFLOW_URL, 'api/experimental/dags/solve_model_dag/dag_runs'),
            json={"conf": conf})

        return {'execution_id': execution_id}, 201

    @Auth.auth_required
    def get(self):
        user_id, admin, super_admin = Auth.return_user_info(request)
        executions = ExecutionModel.get_all_executions_user(user_id)
        ser_executions = execution_schema.dump(executions, many=True)

        return ser_executions, 200
    
    # @Auth.auth_required
    # def get(self):
    #     req_data = request.get_json()
    #     execution_data = ExecutionModel.get_execution_data(req_data["execution_id"])
    #     return execution_data, 200

