"""
Internal endpoint for getting and posting execution data
This are the endpoints used by airflow in its communication with cornflow
"""

from flask import request
from flask_restful import Resource

from ..models import ExecutionModel
from ..schemas import ExecutionSchema
from ..shared import Auth

execution_schema = ExecutionSchema()


class DAGEndpoint(Resource):
    """
    Endpoint used for the DAG endpoint
    """
    # TODO: this endpoint should be a PUT actually, as the execution is also created
    #  and airflow is only writing the results to the needed fields
    @Auth.super_admin_required
    def post(self, reference_id):
        """
        API method to post the results of the execution
        :param reference_id: ID of the execution
        """
        # TODO: control errors and give back error message and error status,
        #  for example if there is a problem with the data validation
        req_data = request.get_json()
        execution = ExecutionModel.get_execution_with_reference(reference_id)
        execution.update(req_data)
        execution.finished = True
        execution.save()
        return {}, 201
    
    @Auth.super_admin_required
    def get(self, reference_id):
        """
        API method to get the data of the instance that is going to be executed
        :param reference_id: ID of the execution
        """
        # TODO: control errors and give back error message and error status,
        #  for example if there is no data.
        execution_data = ExecutionModel.get_execution_data(reference_id)
        return execution_data, 200
