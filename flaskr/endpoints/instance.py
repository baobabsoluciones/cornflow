from flask import request
from flask_restful import Resource
from marshmallow import ValidationError

from ..models.instance import InstanceModel
from ..schemas.instance import InstanceSchema
from ..shared.authentication import Auth

instance_schema = InstanceSchema()


class InstanceEndpoint(Resource):

    @Auth.auth_required
    def get(self):
        user_id, admin, super_admin = Auth.return_user_info(request)
        instance = InstanceModel.get_all_instances_from_user(user_id)
        many = True
        ser_instances = instance_schema.dump(instance, many=many)

        return ser_instances, 200

    @Auth.auth_required
    def post(self):
        req_data = request.get_json()
        try:
            # TODO: do we need partial? I think we need to validate it 100%?
            data = instance_schema.load(req_data, partial=True)
        except ValidationError as err:
            return {'error': 'Wrong JSON format.'}, 400

        data['user_id'], admin, super_admin = Auth.return_user_info(request)

        try:
            instance = InstanceModel(data)
        except KeyError as err:
            return {'error': "Missing information: {}".format(err)}, 400

        instance.save()

        ser_data = instance_schema.dump(instance)

        return {'instance_id': ser_data.get('reference_id')}, 201

class InstanceDetailsEndpoint(Resource):

    @Auth.auth_required
    def get(self, reference_id):
        user_id, admin, super_admin = Auth.return_user_info(request)
        instance = InstanceModel.get_instance_from_user(user_id, reference_id)
        if not instance:
            return {'error': "Instance does not exist."}, 404
        ser_instance = instance_schema.dump(instance, many=False)
        return ser_instance, 200

    @Auth.auth_required
    def delete(self, reference_id):
        user_id, admin, super_admin = Auth.return_user_info(request)
        instance = InstanceModel.get_instance_from_user(user_id, reference_id)
        if not instance:
            return {'error': "Instance does not exist."}, 404
        for execution in instance.executions:
            execution.delete()
        instance.delete()
        return {}, 204


class InstanceFileEndpoint(Resource):

    def post(self):
        pass