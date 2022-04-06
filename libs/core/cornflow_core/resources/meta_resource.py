from flask_restful import Resource


class BaseMetaResource(Resource):
    DESCRIPTION = ""

    def __init__(self):
        super().__init__()
        pass

    def get_list(self):
        pass

    def get_detail(self):
        pass

    def post_list(self):
        pass

    def put_detail(self):
        pass

    def patch_detail(self):
        pass

    def delete_detail(self):
        pass

    def disable_detail(self):
        pass

    def activate_detail(self):
        pass
