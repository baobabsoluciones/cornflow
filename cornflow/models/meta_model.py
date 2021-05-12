"""

"""
import datetime

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import TEXT


from ..shared.utils import db, hash_json_256


class TraceAttributes(db.Model):
    """

    """
    __abstract__ = True
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def __init__(self):
        self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()
        self.deleted_at = None

    def update(self, data):
        self.updated_at = datetime.datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def disable(self):
        self.deleted_at = datetime.datetime.utcnow()
        db.session.add(self)
        db.session.commit()


class BaseDataModel(TraceAttributes):
    """

    """
    __abstract__ = True

    data = db.Column(JSON, nullable=True)
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(TEXT, nullable=True)
    data_hash = db.Column(db.String(256), nullable=False)

    @declared_attr
    def user_id(cls):
        return db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __init__(self, data):
        self.user_id = data.get('user_id')
        self.data = data.get('data') or data.get('execution_results')
        self.data_hash = hash_json_256(self.data)
        self.name = data.get('name')
        self.description = data.get('description')
        super().__init__()

    @classmethod
    def get_all_objects(cls,
                        user,
                        data_schema=None,
                        creation_date_gte=None,
                        creation_date_lte=None,
                        offset=0,
                        limit=10):
        """
        Query to get all objects from a user

        :param UserModel user: User object.
        :param string data_schema: data_schema to filter (dag)
        :param string creation_date_gte: created_at needs to be larger or equal to this
        :param string creation_date_lte: created_at needs to be smaller or equal to this
        :param int offset: query offset for pagination
        :param int limit: query size limit
        :return: The objects
        :rtype: list(:class:`BaseDataModel`)
        """
        query = cls.query.filter(cls.deleted_at == None)
        # TODO: in airflow they use: query = session.query(ExecutionModel)
        if not user.is_admin():
            query = query.filter(cls.user_id == user.id)

        if data_schema:
            query = query.filter(cls.dag_name == data_schema)
        if creation_date_gte:
            query = query.filter(cls.created_at >= creation_date_gte)
        if creation_date_lte:
            query = query.filter(cls.created_at <= creation_date_lte)
        # if airflow they also return total_entries = query.count(), for some reason

        return query.order_by(desc(cls.created_at)).\
            offset(offset).limit(limit).all()

    @classmethod
    def get_one_object_from_user(cls, user, idx):
        """
        Query to get one object from the user and the id.

        :param UserModel user: user object performing the query
        :param str idx: ID from the object to get
        :return: The object or None if it does not exist
        :rtype: :class:`BaseDataModel`
        """
        query = cls.query.filter_by(id=idx, deleted_at=None)
        if not user.is_admin():
            query = query.filter_by(user_id=user.id)
        return query.first()
