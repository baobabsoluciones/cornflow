import datetime
from . import bcrypt
from . import db
from sqlalchemy.sql import expression


class UserModel(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=True)
    admin = db.Column(db.Boolean(), server_default=expression.false(), default=False, nullable=False)
    super_admin = db.Column(db.Boolean(), server_default=expression.false(), default=False, nullable=False)
    created_at = db.Column(db.DateTime)
    modified_at = db.Column(db.DateTime)
    instances = db.relationship('InstanceModel', backref='users', lazy=True)

    def __init__(self, data):
        """

        :param data:
        """

        self.name = data.get('name')
        self.email = data.get('email')
        self.password = self.__generate_hash(data.get('password'))
        self.admin = False
        self.super_admin = False
        self.created_at = datetime.datetime.utcnow()
        self.modified_at = datetime.datetime.utcnow()

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

        self.modified_at = datetime.datetime.utcnow()
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

    # TODO: instead we should define functions with is_admin(user) and is_super_admin(user)
    @staticmethod
    def get_user_info(id):
        user = UserModel.query.get(id)
        return user.admin, user.super_admin

    def __repr__(self):
        return '<id {}>'.format(self.id)
