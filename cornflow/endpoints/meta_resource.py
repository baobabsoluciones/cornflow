"""
Meta resource used in the endpoints to generalize the methods and how they work in order to make all endpoints the same.
It should allow all CRUD (create, read, update, delete) operations
"""
# Import from libraries
from flask_restful import Resource
from flask import request

# Import from internal modules
from ..shared.exceptions import InvalidUsage, ObjectDoesNotExist, NoPermission
from ..shared.authentication import Auth


class MetaResource(Resource):
    # method_decorators = [Auth.auth_required]

    def __init__(self):
        super().__init__()
        self.user = None
        self.model = None
        self.query = None
        self.primary_key = None
        self.dependents = None
        self.foreign_data = None

    def get_user(self):
        if self.user is None:
            self.user = Auth.get_user_obj_from_header(request.headers)
            if self.user is None:
                raise InvalidUsage("Error authenticating user")
        return self.user

    def get_user_id(self):
        return self.get_user().id

    def is_admin(self):
        return self.get_user().admin or self.get_user().super_admin

    def is_super_admin(self):
        return self.get_user().super_admin

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
        data['user_id'] = self.get_user_id()
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

        item = getattr(self.model, self.query)(*args)
        if item is None:
            raise ObjectDoesNotExist()

        data = dict(data)
        data['user_id'] = self.get_user_id()
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
        if self.get_user().id != owner:
            return False
        else:
            return True
