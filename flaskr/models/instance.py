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
        """

        :param dict data:
        """
        super().__init__(data)
        self.user_id = data.get('user_id')
        self.data = data.get('data')
        self.name = data.get('data')['parameters']['name']
        # TODO: check if reference id for the instance can be modified to either be smaller or have a prefix
        #  that identifies it as an instance
        self.reference_id = hashlib.sha1((str(self.created_at) + ' ' + str(self.user_id)).encode()).hexdigest()

    def save(self):
        """

        :return:
        :rtype:
        """
        db.session.add(self)
        db.session.commit()

    def update(self, data):
        """

        :param dict data:
        :return:
        :rtype:
        """
        for key, item in data.items():
            setattr(self, key, item)
        super().__init__()

    def disable(self):
        """
        Updates the deleted_at field of an execution to mark an execution as "deleted"

        :return:
        :rtype:
        """
        super().disable()

    def delete(self):
        """

        :return:
        :rtype:
        """
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def get_all_instances(user):
        """

        :param int user:
        :return:
        :rtype:
        """
        return InstanceModel.query.filter_by(user_id=user, deleted_at=None)

    @staticmethod
    def get_one_instance_from_id(internal_id):
        """

        :param int internal_id:
        :return:
        :rtype:
        """
        return InstanceModel.query.get(internal_id, deleted_at=None)

    @staticmethod
    def get_one_instance_from_reference(reference):
        """

        :param str reference:
        :return:
        :rtype:
        """
        return InstanceModel.query.filter_by(reference_id=reference, deleted_at=None).first()

    @staticmethod
    def get_one_instance_from_user(user, reference):
        """

        :param int user:
        :param str reference:
        :return:
        :rtype:
        """
        return InstanceModel.get_all_instances(user=user).filter_by(reference_id=reference).first()

    @staticmethod
    def get_instance_id(reference):
        """

        :param str reference:
        :return:
        :rtype:
        """
        return InstanceModel.get_one_instance_from_reference(reference).id

    @staticmethod
    def get_instance_owner(reference):
        """

        :param str reference:
        :return:
        :rtype:
        """
        return InstanceModel.get_one_instance_from_reference(reference).user_id

    def __repr__(self):
        """

        :return:
        :rtype:
        """
        return '<id {}>'.format(self.id)


