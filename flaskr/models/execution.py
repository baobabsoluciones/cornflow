import datetime
import hashlib

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.sql import expression

from ..shared.utils import db
from ..models.instance import InstanceModel
from .meta_model import BaseAttributes


class ExecutionModel(BaseAttributes):
    """

    """

    __tablename__ = 'executions'

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey('instances.id'), nullable=False)
    config = db.Column(JSON, nullable = False)
    reference_id = db.Column(db.String(256), nullable=False, unique=True)
    execution_results = db.Column(JSON, nullable=True)
    log_text = db.Column(TEXT, nullable=True)
    log_json = db.Column(JSON, nullable=True)
    finished = db.Column(db.Boolean, server_default=expression.false(), default=False, nullable=False)

    def __init__(self, data):
        super().__init__()
        self.user_id = data.get('user_id')
        self.instance_id = data.get('instance_id')
        self.finished = False
        self.config = data.get('config')
        self.created_at = datetime.datetime.utcnow()
        self.modified_at = datetime.datetime.utcnow()
        # TODO: check if reference id for the instance can be modified to either be smaller or have a prefix
        #  that identifies it as an execution
        self.reference_id = hashlib.sha1(
            (str(self.created_at) + ' ' + str(self.user_id) + ' ' + str(self.instance_id)).encode()).hexdigest()

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
    def get_all_executions_user(user):
        return ExecutionModel.query.filter_by(user_id=user)
    
    @staticmethod
    def get_one_execution(id):
        return ExecutionModel.query.get(id)

    @staticmethod
    def get_execution_with_id(id):
        return ExecutionModel.query.get(id)

    @staticmethod
    def get_execution_with_reference(reference_id):
        return ExecutionModel.query.filter_by(reference_id=reference_id).first()

    @staticmethod
    def get_execution_id(reference_id):
        return ExecutionModel.query.filter_by(reference_id=reference_id).first().id
    
    @staticmethod
    def get_execution_data(reference_id):
        id = ExecutionModel.get_execution_id(reference_id)
        print("id", id)
        execution = ExecutionModel.get_one_execution(id)
        print("execution", execution)
        instance_data = InstanceModel.get_one_instance(execution.instance_id).data
        print(instance_data)
        config = execution.config
        return {"data":instance_data, "config":config}
        
    def __repr__(self):
        return '<id {}>'.format(self.id)


