from flaskr.models.user import UserModel, UserSchema
from flaskr.shared.authentication import Auth
from flaskr.shared.resource import BaseResource

user_schema = UserSchema()


class UserEndpoint(BaseResource):

    @Auth.auth_required
    def get(self):
        users = UserModel.get_all_users()
        ser_users = user_schema.dump(users, many=True)
        return ser_users, 200
