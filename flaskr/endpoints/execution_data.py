"""

Internal endpoint for getting and posting execution data

"""

import requests

from flask import request
from flask_restful import Resource

from ..models.execution import ExecutionModel
from ..models.instance import InstanceModel
from ..schemas.execution_schema import ExecutionSchema
from ..shared.authentication import Auth

execution_schema = ExecutionSchema()


class ExecutionDataEndpoint(Resource):
    
    @Auth.auth_required
    def post(self):
        print("posting results")
        req_data = request.get_json()
        print(req_data)
        reference_id = req_data["execution_id"]
        print(reference_id)
        id = ExecutionModel.get_execution_id(reference_id)
        print(id)
        execution = ExecutionModel.get_one_execution(id)
        print(execution)
        execution.update(req_data)
        execution.save()
        return {}, 201
    
    @Auth.auth_required
    def get(self):
        req_data = request.get_json()
        execution_data = ExecutionModel.get_execution_data(req_data["execution_id"])
        return execution_data, 200
