"""

Internal endpoint for getting and posting execution data
This are the endpoints used by airflow in its communication with cornflow

"""

import requests

from flask import request
from flask_restful import Resource

from ..models.execution import ExecutionModel
from ..models.instance import InstanceModel
from ..schemas.execution import ExecutionSchema
from ..shared.authentication import Auth

execution_schema = ExecutionSchema()


class DAGEndpoint(Resource):
    
    @Auth.super_admin_required
    def post(self, reference_id):
        req_data = request.get_json()
        execution = ExecutionModel.get_execution_with_reference_admin(reference_id)
        execution.update(req_data)
        execution.finished = True
        execution.save()
        return {}, 201
    
    @Auth.super_admin_required
    def get(self, reference_id):
        execution_data = ExecutionModel.get_execution_data_admin(reference_id)
        return execution_data, 200
