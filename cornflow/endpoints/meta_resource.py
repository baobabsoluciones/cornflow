"""
Meta resource used in the endpoints to generalize the methods and how they work in order to make all endpoints the same.
It should allow all CRUD (create, read, update, delete) operations
"""
# Import from libraries
from flask_restful import Resource
from marshmallow.exceptions import ValidationError
# Import from internal modules


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
        self.primary_key = None
        self.dependents = None
        self.foreign_data = None
        self.foreign_owner = None

    def get_list(self, *args):
        self.data = getattr(self.model, self.query)(*args)
        self.serialized_data = self.schema.dump(self.data, many=True)
        if len(self.serialized_data) == 0:
            return {}, 204
        else:
            return self.serialized_data, 200

    def get_detail(self, *args):
        self.data = getattr(self.model, self.query)(*args)
        self.serialized_data = self.schema.dump(self.data, many=False)
        if len(self.serialized_data) == 0:
            return {}, 204
        else:
            return self.serialized_data, 200

    def post_list(self, request):
        request_data = request.get_json()
        try:
            self.data = self.schema.load(request_data, partial=True)
        except ValidationError as val_err:
            return {'error': val_err.normalized_messages()}, 400

        self.data['user_id'] = self.user_id

        item = self.model(self.data)

        if self.foreign_data is not None:
            for fk in self.foreign_data:
                self.foreign_owner = self.foreign_data[fk].query.get(getattr(item, fk)).user_id
                if not self.check_permissions():
                    return {'error': 'You do not have to create this object.'}, 400

        item.save()

        return {self.primary_key: getattr(item, self.primary_key)}, 201

    def put_detail(self, request, *args):

        request_data = request.get_json()

        try:
            self.data = self.schema.load(request_data, partial=True)
        except ValidationError as val_err:
            return {'error': val_err.normalized_messages()}, 400

        self.data['user_id'] = self.user_id

        item = getattr(self.model, self.query)(*args)
        if item is None:
            # TODO: why is sometimes 'message' and sometimes 'error' when it's 400
            return {'message': 'The object to update does not exist.'}, 400
        item.update(self.data)

        return {'message': 'Updated correctly.'}, 200

    def delete_detail(self, *args):

        item = getattr(self.model, self.query)(*args)

        if item is None:
            return {'message': 'The object to delete does not exist.'}, 400

        # TODO: I think there's a model configuration in django to do this automatically.
        #  In this case, what happens when there are more than one "dependents"?
        if self.dependents is not None:
            for element in getattr(item, self.dependents):
                element.disable()
        if item:
            item.disable()

        return {'message': 'The object has been deleted'}, 200

    def check_permissions(self):
        if self.user_id != self.foreign_owner:
            return False
        else:
            return True
