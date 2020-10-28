import datetime

from marshmallow import fields, Schema
from sqlalchemy.sql import expression

from ..schemas.instance_schema import InstanceSchema
from ..shared.utils import bcrypt, db

from .base_attributes import TraceAttributes


class UserModel(TraceAttributes):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=True)
    admin = db.Column(db.Boolean(), server_default=expression.false(), default=False, nullable=False)
    super_admin = db.Column(db.Boolean(), server_default=expression.false(), default=False, nullable=False)
    instances = db.relationship('InstanceModel', backref='users', lazy=True)

    def __init__(self, data):
        """

        :param data:
        """
        super().__init__()
        self.name = data.get('name')
        self.email = data.get('email')
        self.password = self.__generate_hash(data.get('password'))
        self.admin = False
        self.super_admin = False

    def save(self):
        db.session.add(self)
        db.session.commit()

    def update(self, data):
        for key, item in data.items():
            if key == 'password':
                self.password = self.__generate_hash(item)
            elif key == 'admin' or key == 'super_admin':
                continue
            setattr(self, key, item)

        super().__init__()
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def __generate_hash(self, password):
        return bcrypt.generate_password_hash(password, rounds=10).decode('utf8')

    def check_hash(self, password):
        return bcrypt.check_password_hash(self.password, password)

    @staticmethod
    def get_all_users():
        return UserModel.query.all()

    @staticmethod
    def get_one_user(id):
        return UserModel.query.get(id)

    @staticmethod
    def get_one_user_by_email(em):
        return UserModel.query.filter_by(email=em).first()

    @staticmethod
    def get_user_info(id):
        user = UserModel.query.get(id)
        return user.admin, user.super_admin

    def __repr__(self):
        return '<id {}>'.format(self.id)


class UserSchema(Schema):
    """

    """
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    admin = fields.Boolean(required=False, load_only=True)
    super_admin = fields.Boolean(required=False, load_only=True)
    created_at = fields.DateTime(dump_only=True)
    modified_at = fields.DateTime(dump_only=True)
    instances = fields.Nested(InstanceSchema, many=True)
