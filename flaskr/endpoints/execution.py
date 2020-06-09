from flask import request
from flask_restful import Resource

from flaskr.models.execution import ExecutionModel, ExecutionSchema
from flaskr.models.instance import InstanceModel
from flaskr.shared.authentication import Auth

execution_schema = ExecutionSchema()

class ExecutionEndpoint(Resource):

    @Auth.auth_required
    def post(self):
        req_data = request.get_json()
        data = execution_schema.load(req_data, partial=True)

        data['user_id'] = Auth.return_user(request)
        data['instance_id'] = InstanceModel.get_instance_id(data['instance'])

        execution = ExecutionModel(data)
        execution.save()

        ser_data = execution_schema.dump(execution)

        return {'execution_id': ser_data.get('reference_id')}, 201

    @Auth.auth_required
    def get(self):
        user_id = Auth.return_user(request)
        executions = ExecutionModel.get_all_executions_user(user_id)
        ser_executions = execution_schema.dump(executions, many=True)

        return ser_executions, 200

