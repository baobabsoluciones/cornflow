import datetime
import hashlib

from sqlalchemy.dialects.postgresql import JSON
from flaskr.schemas.execution_schema import *
from flaskr.schemas.model_schema import *
#from flaskr.models.execution import ExecutionSchema
from . import db
from flaskr.schemas.model_schema import *


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
    def get_instance_id(reference):
        return InstanceModel.query.filter_by(reference_id=reference).first().id

    def __repr__(self):
        return '<id {}>'.format(self.id)


class ExecutionSchema(Schema):
    """

    """
    id = fields.Int(dump_only=True, load_only=True)
    user_id = fields.Int(required=False, load_only=True)
    instance_id = fields.Int(required=False, dump_only=True, load_only=True)
    instance = fields.Str(required=True)
    config = fields.Nested(ConfigSchema, required=True)
    reference_id = fields.Str(dump_only=True)
    execution_results = fields.Nested(DataSchema, dump_only=True)
    log_text = fields.Str(dump_only=True)
    log_json = fields.Nested(LogSchema, dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    modified_at = fields.DateTime(dump_only=True)


class InstanceSchema(Schema):
    """

    """
    id = fields.Int(dump_only=True, load_only=True)
    user_id = fields.Int(required=False, load_only=True)
    data = fields.Nested(DataSchema, required=True, load_only=True)
    name = fields.Str(dump_only=True)
    reference_id = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    modified_at = fields.DateTime(dump_only=True)
    executions = fields.Nested(ExecutionSchema, many=True)

