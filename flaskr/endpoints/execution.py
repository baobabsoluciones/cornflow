
from flask import request, current_app
from flask_restful import Resource

from ..models.execution import ExecutionModel
from ..models.instance import InstanceModel
from ..schemas.execution_schema import ExecutionSchema
from ..shared.authentication import Auth
from ..shared.errors import AirflowError

from ..shared.airflow_api import Airflow

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
        # To send the absolute url:
        # url_for(endpoint_name, _external=True)
        airflow_client = Airflow(current_app.config['AIRFLOW_URL'])
        response = airflow_client.run_dag(execution_id, current_app.config['CORNFLOW_URL'])
        if response.status_code != 200:
            raise AirflowError('Airflow responded with a status: {}:\n{}'.
                               format(response.status_code, response.text))

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

