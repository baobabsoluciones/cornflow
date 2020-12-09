"""
Meta resource used in the endpoints to generalize the methods and how they work in order to make all endpoints the same.
It should allow all CRUD (create, read, update, delete) operations
"""
# Import from libraries
from flask_restful import Resource
from marshmallow.exceptions import ValidationError
# Import from internal modules
from ..shared import Auth


class MetaResource(Resource):
    # method_decorators = [Auth.auth_required]

    def __init__(self):
        super().__init__()
        self.user_id = None
        self.admin = None
        self.super_admin = None
        self.data = None
        self.model = None
        self.query = None
        self.serialized_data = None
        self.schema = None
        self.external_primary_key = None
        self.internal_primary_key = None
        self.output_name = None

        pass

    @Auth.auth_required
    def get_list(self, request):
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        # TODO: what if there is no instances?
        self.data = getattr(self.model, self.query)(self.user_id)
        self.serialized_data = self.schema.dump(self.data, many=True)

        return self.serialized_data, 200

    @Auth.auth_required
    def get_detail(self, request, idx):
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        self.data = getattr(self.model, self.query)(idx)
        self.serialized_data = self.schema.dump(self.data, many=False)

        return self.serialized_data, 200

    @Auth.auth_required
    def post_list(self, request):
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        request_data = request.get_json()
        try:
            self.data = self.schema.load(request_data, partial=True)
        except ValidationError as val_err:
            return {'error': val_err.normalized_messages()}, 400

        self.data['user_id'] = self.user_id

        instance = self.model(self.data)
        instance.save()

        self.serialized_data = self.schema.dump(self.data)

        return {self.output_name: self.ser_data.get(self.external_primary_key)}, 201

    @Auth.auth_required
    def put_detail(self, request, idx):
        return {}, 501

    @Auth.auth_required
    def delete_detail(self, request, idx):
        return {}, 501
