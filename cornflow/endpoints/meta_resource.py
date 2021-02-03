"""
Meta resource used in the endpoints to generalize the methods and how they work in order to make all endpoints the same.
It should allow all CRUD (create, read, update, delete) operations
"""
# Import from libraries
from flask_restful import Resource
from marshmallow.exceptions import ValidationError
from ..shared.exceptions import InvalidUsage, ObjectDoesNotExist, NoPermission
# Import from internal modules


class MetaResource(Resource):
    # method_decorators = [Auth.auth_required]

    def __init__(self):
        super().__init__()
        self.user_id = None
        self.admin = None
        self.super_admin = None
        self.model = None
        self.query = None
        self.schema = None
        self.primary_key = None
        self.dependents = None
        self.foreign_data = None

    def get_list(self, *args):
        data = getattr(self.model, self.query)(*args)
        return data, 200

    def get_detail(self, *args):
        data = getattr(self.model, self.query)(*args)
        if data is None:
            raise ObjectDoesNotExist()
        else:
            return data, 200

    def post_list(self, data):
        data = dict(data)
        data['user_id'] = self.user_id
        item = self.model(data)
        if self.foreign_data is not None:
            for fk in self.foreign_data:
                owner = self.foreign_data[fk].query.get(getattr(item, fk))
                if owner is None:
                    raise NoPermission()
                if not self.check_permissions(owner.user_id):
                    raise NoPermission()
        item.save()

        return {self.primary_key: getattr(item, self.primary_key)}, 201

    def put_detail(self, data, *args):

        data = dict(data)
        data['user_id'] = self.user_id

        item = getattr(self.model, self.query)(*args)
        if item is None:
            raise ObjectDoesNotExist()
        item.update(data)

        return {'message': 'Updated correctly'}, 200

    def delete_detail(self, *args):

        item = getattr(self.model, self.query)(*args)

        if item is None:
            raise ObjectDoesNotExist()

        if self.dependents is not None:
            for element in getattr(item, self.dependents):
                element.disable()
        if item:
            item.disable()

        return {'message': 'The object has been deleted'}, 200

    def check_permissions(self, owner):
        if self.user_id != owner:
            return False
        else:
            return True
