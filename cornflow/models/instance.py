"""Model for the instances"""

# Import from libraries
import hashlib

# Import from sqlalchemy
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import TEXT

# Imported from internal models
from .meta_model import BaseAttributes
from ..shared.utils import db


class InstanceModel(BaseAttributes):
    """
    Model class for the Instances
    It inherits from :class:`BaseAttributes` to have the trace fields and user field

    The :class:`InstanceModel` has the following fields:

    - **id**: int, the primary key for the executions, it is also referred as the internal ID.
    - **data**: dict (JSON), the data structure of the instance (:class:`DataSchema`)
    - **name**: str, the name given to the instance by the user.
    - **reference_id**: str, a hash generated upon creation of the instance and the id given back to the user.
      The hash is generated from the creation time and the user id.
      This field is unique for each instance.
    - **executions**: relationship, not a field in the model but the relationship between the _class:`InstanceModel`
      and its dependent :class:`ExecutionModel`.
    - **user_id**: int, the foreign key for the user (:class:`UserModel`). It links the execution to its owner.
    - **created_at**: datetime, the datetime when the execution was created (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **updated_at**: datetime, the datetime when the execution was last updated (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **deleted_at**: datetime, the datetime when the execution was deleted (in UTC). Even though it is deleted,
      actually, it is not deleted from the database, in order to have a command that cleans up deleted data
      after a certain time of its deletion.
      This datetime is generated automatically, the user does not need to provide it.

    :param dict data: the aprsed json got from an endpoint that contains all the required information to create
      a new instance
    """

    # Table name in the database
    __tablename__ = 'instances'

    # Model fields
    id = db.Column(db.String(256), nullable=False, primary_key=True)
    data = db.Column(JSON, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(TEXT, nullable=True)
    executions = db.relationship('ExecutionModel', backref='instances', lazy=True)

    def __init__(self, data):
        super().__init__(data)
        # TODO: check if reference id for the instance can be modified to either be smaller or have a prefix
        #  that identifies it as an instance
        self.id = hashlib.sha1((str(self.created_at) + ' ' + str(self.user_id)).encode()).hexdigest()
        self.data = data.get('data')
        self.name = data.get('name')
        self.description = data.get('description')

    def save(self):
        """
        Saves the instance to the data base

        :return:
        :rtype:
        """
        db.session.add(self)
        db.session.commit()

    def update(self, data):
        """
        Updates the execution in the data base and automatically updates the updated_at field

        :param dict data: A dictionary containing the updated data for the instance
        :return:
        :rtype:
        """
        for key, item in data.items():
            setattr(self, key, item)
        super().update(data)

    def disable(self):
        """
        Updates the deleted_at field of an execution to mark an execution as "deleted"

        :return:
        :rtype:
        """
        super().disable()

    def delete(self):
        """
        Deletes an instance permanently from the data base

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
    def get_one_instance_from_id(idx):
        """

        :param str idx:
        :return:
        :rtype:
        """
        return InstanceModel.query.get(idx, deleted_at=None)

    @staticmethod
    def get_one_instance_from_user(user, idx):
        """

        :param int user:
        :param str idx:
        :return:
        :rtype:
        """
        return InstanceModel.query.filter_by(user_id=user, id=idx, deleted_at=None).first()

    @staticmethod
    def get_instance_owner(idx):
        """

        :param str idx:
        :return:
        :rtype:
        """
        return InstanceModel.query.get(idx).user_id

    def __repr__(self):
        """

        :return:
        :rtype:
        """
        return '<id {}>'.format(self.id)


