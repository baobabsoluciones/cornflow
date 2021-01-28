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

    - **id**: int, the primary key for the executions, a hash generated upon creation of the instance 
      and the id given back to the user.The hash is generated from the creation time and the user id.
    - **data**: dict (JSON), the data structure of the instance (:class:`DataSchema`)
    - **name**: str, the name given to the instance by the user.
    - **description**: str, the description given to the instance by the user. It is optional.
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

    :param dict data: the parsed json got from an endpoint that contains all the required information to create
      a new instance
    """

    # Table name in the database
    __tablename__ = 'instances'

    # Model fields
    id = db.Column(db.String(256), nullable=False, primary_key=True)
    data = db.Column(JSON, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(TEXT, nullable=True)
    executions = db.relationship('ExecutionModel', backref='instances', lazy=True,
                                 primaryjoin="and_(InstanceModel.id==ExecutionModel.instance_id, "
                                             "ExecutionModel.deleted_at==None)"
                                 )

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
        """
        db.session.add(self)
        db.session.commit()

    def update(self, data):
        """
        Updates the execution in the data base and automatically updates the updated_at field

        :param dict data: A dictionary containing the updated data for the instance
        """
        for key, item in data.items():
            setattr(self, key, item)
        super().update(data)

    def disable(self):
        """
        Updates the deleted_at field of an execution to mark an execution as "deleted"
        """
        super().disable()

    def delete(self):
        """
        Deletes an instance permanently from the data base
        """
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def get_all_instances_admin():
        """
        Query to get all instances.
        BEWARE: only the admin should do this.

        :return: The instances
        :rtype: list(:class:`InstanceModel`)
        """
        return InstanceModel.query.filter_by(deleted_at=None)

    @staticmethod
    def get_all_instances(user):
        """
        Query to get all instances from a user

        :param int user: ID from the user performing the query
        :return: The instances
        :rtype: list(:class:`InstanceModel`)
        """
        return InstanceModel.query.filter_by(user_id=user, deleted_at=None)

    @staticmethod
    def get_one_instance_from_id(idx):
        """
        Query to get one instance from its ID

        :param str idx: ID from the instance
        :return: The instance
        :rtype: :class:`InstanceModel`
        """
        return InstanceModel.query.filter_by(id=idx, deleted_at=None).first()

    @staticmethod
    def get_one_instance_from_user(user, idx):
        """
        Query to get one instance from the user and the id.

        :param int user: ID from the user performing the query
        :param str idx: ID from the instance
        :return: The instance
        :rtype: :class:`InstanceModel`
        """
        return InstanceModel.query.filter_by(user_id=user, id=idx, deleted_at=None).first()

    def __repr__(self):
        """
        Method to represent the class :class:`InstanceModel`

        :return: The representation of the :class:`InstanceModel`
        :rtype: str
        """
        return '<id {}>'.format(self.id)

    def __str__(self):
        """
        Method to print a string representation of the :class:`InstanceModel`

        :return: The string for the :class:`InstanceModel`
        :rtype: str
        """
        return '<id {}>'.format(self.id)
