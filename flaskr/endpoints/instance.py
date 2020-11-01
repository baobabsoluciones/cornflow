from flask import request
from flask_restful import Resource

from ..models.instance import InstanceModel
from ..schemas.instance import InstanceSchema
from ..shared.authentication import Auth

instance_schema = InstanceSchema()


class InstanceEndpoint(Resource):

    @Auth.auth_required
    def get(self, reference_id=None):
        user_id, admin, super_admin = Auth.return_user_info(request)
        if reference_id is not None:
            instance = InstanceModel.get_instance_from_user(user_id, reference_id)
            many = False
        else:
            instance = InstanceModel.get_all_instances(user_id)
            many = True
        ser_instances = instance_schema.dump(instance, many=many)

        return ser_instances, 200

    @Auth.auth_required
    def post(self):
        req_data = request.get_json()
        # TODO: catch possible validation error and process it to give back a more meaningful error message
        data = instance_schema.load(req_data, partial=True)

        data['user_id'], admin, super_admin = Auth.return_user_info(request)

        instance = InstanceModel(data)
        instance.save()

        ser_data = instance_schema.dump(instance)

        return {'instance_id': ser_data.get('reference_id')}, 201

    @Auth.auth_required
    def delete(self, reference_id):
        user_id, admin, super_admin = Auth.return_user_info(request)
        instance = InstanceModel.get_instance_from_user(user_id, reference_id)

        # TODO: not sure if this is the correct order
        for exec in instance.executions:
            exec.delete()
        if instance:
            instance.delete()
        return {}, 204
