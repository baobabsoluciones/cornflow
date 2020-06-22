from flask_restful import Resource
from flaskr.shared.authentication import Auth

class BaseResource(Resource):
    # method_decorators = [Auth.auth_required]
    pass