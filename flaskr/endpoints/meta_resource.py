"""
Meta resource used in the endpoints to generalize the methods and how they work in order to make all endpoints the same.
It should allow all CRUD (create, read, update, delete) operations
"""
# Import from libraries
from flask_restful import Resource

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

        pass

    @Auth.auth_required
    def get_list(self, request):
        self.user_id, self.admin, self.super_admin = Auth.return_user_info(request)
        self.data = getattr(self.model, self.query)(self.user_id)
        self.serialized_data = self.schema.dump(self.data, many=True)

        return self.serialized_data, 200
