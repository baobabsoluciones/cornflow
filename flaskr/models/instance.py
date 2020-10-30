import datetime
import hashlib

from sqlalchemy.dialects.postgresql import JSON
from ..shared.utils import db
from .meta_model import BaseAttributes


class InstanceModel(BaseAttributes):
    """

    """

    __tablename__ = 'instances'

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(JSON, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    reference_id = db.Column(db.String(256), nullable=False, unique=True)
    executions = db.relationship('ExecutionModel', backref='instances', lazy=True)

    def __init__(self, data):
        super().__init__(data)
        self.user_id = data.get('user_id')
        self.data = data.get('data')
        self.name = data.get('data')['parameters']['name']
        # TODO: check if reference id for the instance can be modified to either be smaller or have a prefix
        #  that identifies it as an instance
        self.reference_id = hashlib.sha1((str(self.created_at) + ' ' + str(self.user_id)).encode()).hexdigest()

    def save(self):
        db.session.add(self)
        db.session.commit()

    def update(self, data):
        for key, item in data.items():
            setattr(self, key, item)
        super().__init__()

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
    def get_one_instance_with_reference(reference_id):
        return InstanceModel.query.filter_by(reference_id=reference_id).first()

    @staticmethod
    def get_instance_id(reference):
        return InstanceModel.query.filter_by(reference_id=reference).first().id

    @staticmethod
    def get_instance_owner(reference):
        return InstanceModel.query.filter_by(reference_id=reference).first().user_id

    def __repr__(self):
        return '<id {}>'.format(self.id)


