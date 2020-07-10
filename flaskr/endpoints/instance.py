from flask import request
from flask_restful import Resource

from flaskr.models.instance import InstanceModel
from flaskr.schemas.instance_schema import InstanceSchema
from flaskr.shared.authentication import Auth

instance_schema = InstanceSchema()

class InstanceEndpoint(Resource):

    @Auth.auth_required
    def get(self):
        user_id = Auth.return_user(request)
        instances = InstanceModel.get_all_instances(user_id)
        ser_instances = instance_schema.dump(instances, many=True)

        return ser_instances, 200

    @Auth.auth_required
    def post(self):
        req_data = request.get_json()
        data = instance_schema.load(req_data, partial=True)

        data['user_id'] = Auth.return_user(request)

        instance = InstanceModel(data)
        instance.save()

        ser_data = instance_schema.dump(instance)

        return {'instance_id': ser_data.get('reference_id')}, 201
