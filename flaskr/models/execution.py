import datetime
import hashlib

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import TEXT

from . import db
from flaskr.schemas.execution_schema import *
from flaskr.schemas.model_schema import *


class ExecutionModel(db.Model):
    """

    """

    __tablename__ = 'executions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    instance_id = db.Column(db.Integer, db.ForeignKey('instances.id'), nullable=False)
    config = db.Column(JSON, nullable = False)
    reference_id = db.Column(db.String(256), nullable=False, unique=True)
    execution_results = db.Column(JSON, nullable=True)
    log_text = db.Column(TEXT, nullable=True)
    log_json = db.Column(JSON, nullable=True)
    created_at = db.Column(db.DateTime)
    modified_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.user_id = data.get('user_id')
        self.instance_id = data.get('instance_id')
        self.config = data.get('config')
        self.created_at = datetime.datetime.utcnow()
        self.modified_at = datetime.datetime.utcnow()
        self.reference_id = hashlib.sha1(
            (str(self.created_at) + ' ' + str(self.user_id) + ' ' + str(self.instance_id)).encode()).hexdigest()

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
    def get_all_executions_user(user):
        return ExecutionModel.query.filter_by(user_id=user)

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
