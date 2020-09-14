import requests

from flask import request, current_app
from flask_restful import Resource

from ..models.execution import ExecutionModel
from ..models.instance import InstanceModel
from ..schemas.execution_schema import ExecutionSchema
from ..shared.authentication import Auth

from urllib.parse import urljoin

execution_schema = ExecutionSchema()

class ExecutionEndpoint(Resource):

    @Auth.auth_required
    def post(self):
        req_data = request.get_json()
        data = execution_schema.load(req_data, partial=True)

        data['user_id'], admin, super_admin = Auth.return_user_info(request)
        data['instance_id'] = InstanceModel.get_instance_id(data['instance'])
        instance_owner = InstanceModel.get_instance_owner(data['instance'])

        if instance_owner != data['user_id'] and not super_admin:
            return {'error': 'You do not have permissions for the instance'}, 400

        execution = ExecutionModel(data)
        execution.save()

        ser_data = execution_schema.dump(execution)
        execution_id = ser_data.get('reference_id')
        
        # solve
        conf = "{\"exec_id\":\"%s\"}" % execution_id

        # TODO: process response to check what happened on the airflow side
        # TODO: move airflow calls to its own class

        # TODO: replace cornflow_url with the address of this server (using reverse?)
        response = requests.post(
            urljoin(current_app.config['AIRFLOW_URL'], 'api/experimental/dags/solve_model_dag/dag_runs'),
            json={"conf": conf, "cornflow_url": "http://127.0.0.1:5000"})

        return {'execution_id': execution_id}, 201

    @Auth.auth_required
    def get(self):
        user_id, admin, super_admin = Auth.return_user_info(request)
        executions = ExecutionModel.get_all_executions_user(user_id)
        ser_executions = execution_schema.dump(executions, many=True)

        return ser_executions, 200


class ExecutionDetailsEndpoint(Resource):

    @Auth.auth_required
    def get(self, reference_id):
        execution = ExecutionModel.get_execution_with_reference(reference_id)
        ser_execution = execution_schema.dump(execution, many=False)

        return ser_execution, 200


class ExecutionStatusEndpoint(Resource):

    # TODO: call airflow to check status
    @Auth.auth_required
    def get(self, reference_id):
        status = ExecutionModel.get_execution_with_reference(reference_id).finished

        if not status:
            # Here we should call airflow to check solving status
            pass

        return {'finished': status}, 200

