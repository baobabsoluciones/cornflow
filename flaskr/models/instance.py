import datetime
import hashlib

from sqlalchemy.dialects.postgresql import JSON
from . import db


class InstanceModel(db.Model):
    """

    """

    __tablename__ = 'instances'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data = db.Column(JSON, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    reference_id = db.Column(db.String(256), nullable=False, unique=True)
    created_at = db.Column(db.DateTime)
    modified_at = db.Column(db.DateTime)
    executions = db.relationship('ExecutionModel', backref='instances', lazy=True)

    def __init__(self, data):
        self.user_id = data.get('user_id')
        self.data = data.get('data')
        self.created_at = datetime.datetime.utcnow()
        self.modified_at = datetime.datetime.utcnow()
        self.name = data.get('data')['parameters']['name']
        self.reference_id = hashlib.sha1((str(self.created_at) + ' ' + str(self.user_id)).encode()).hexdigest()

    def save(self):
        db.session.add(self)
        db.session.commit()

    def update(self, data):
        for key, item in data.items():
            setattr(self, key, item)
        self.modified_at = datetime.datetime.utcnow()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def get_all_instances(user):
        return InstanceModel.query.filter_by(user_id=user)

    @staticmethod
    def get_one_instance(id):
        return InstanceModel.query.get(id)

    @staticmethod
    def get_instance(reference):
        return InstanceModel.query.filter_by(reference_id=reference).first()

    @staticmethod
    def get_instance_from_user(user, reference):
        return InstanceModel.get_all_instances(user=user).filter_by(reference_id=reference).first()

    @staticmethod
    def get_instance_id(reference):
        return InstanceModel.get_instance(reference).id

    @staticmethod
    def get_instance_owner(reference):
        return InstanceModel.get_instance(reference).user_id

    def __repr__(self):
        return '<id {}>'.format(self.id)


