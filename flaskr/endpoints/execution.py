
from flask import request, current_app
from flask_restful import Resource
from marshmallow import ValidationError

from ..models.execution import ExecutionModel
from ..models.instance import InstanceModel
from ..schemas.execution import ExecutionSchema
from ..shared.authentication import Auth
from ..shared.airflow_api import Airflow, AirflowApiError

execution_schema = ExecutionSchema()


class ExecutionEndpoint(Resource):

    @Auth.auth_required
    def post(self):
        req_data = request.get_json()
        try:
            data = execution_schema.load(req_data, partial=True)
        except ValidationError as err:
            return {'error': 'Wrong JSON format: {}'.format(err)}, 400

        try:
            user_id, admin, super_admin = Auth.return_user_info(request)
            instance_obj = InstanceModel.get_instance_from_user(user_id, data['instance'])
            if not instance_obj:
                return {'error': 'No instance corresponds to that reference'}, 404
            data['user_id'] = user_id
            data['instance_id'] = instance_obj.id
            execution = ExecutionModel(data)
        except KeyError as err:
            return {'error': "Missing information: {}".format(err)}, 400

        execution.save()

        ser_data = execution_schema.dump(execution)
        execution_id = ser_data.get('reference_id')
        
        # solve
        # To send the absolute url:
        # url_for(endpoint_name, _external=True)
        airflow_client = Airflow(current_app.config['AIRFLOW_URL'],
                                 current_app.config['AIRFLOW_USER'],
                                 current_app.config['AIRFLOW_PWD'])
        if not airflow_client.is_alive():
            return {'error': "Airflow is not accesible"}, 400
        try:
            airflow_client.run_dag(execution_id, current_app.config['CORNFLOW_URL'])
        except AirflowApiError:
            return {'error': "Airflow responded with an error"}, 400

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
        user_id, admin, super_admin = Auth.return_user_info(request)
        execution = ExecutionModel.get_execution_from_user(user_id, reference_id)
        # TODO: here, the execution log progress is read correctly.
        #  but later, during the schema matching, the arrays in the progress are converted
        #  into strings
        # print(execution.log_json['progress'][1])
        if not execution:
            return {}, 404
        ser_execution = execution_schema.dump(execution, many=False)
        # print(ser_execution['log_json']['progress'])
        return ser_execution, 200

    @Auth.auth_required
    def delete(self, reference_id):
        user_id, admin, super_admin = Auth.return_user_info(request)
        execution = ExecutionModel.get_execution_from_user(user_id, reference_id)
        if not execution:
            return {}, 404
        execution.delete()
        return {}, 204


class ExecutionStatusEndpoint(Resource):

    # TODO: call airflow to check status
    @Auth.auth_required
    def get(self, reference_id):
        status = ExecutionModel.get_execution_from_user(reference_id).finished

        if not status:
            # Here we should call airflow to check solving status
            pass

        return {'finished': status}, 200

