"""

"""

from flask import current_app
from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.ext.declarative import declared_attr

from cornflow.models.meta_models import TraceAttributesModel
from cornflow.shared import db
from cornflow.shared.utils import hash_json_256


class BaseDataModel(TraceAttributesModel):
    """ """

    __abstract__ = True

    data = db.Column(JSON, nullable=True)
    checks = db.Column(JSON, nullable=True)
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(TEXT, nullable=True)
    data_hash = db.Column(db.String(256), nullable=False)
    schema = db.Column(db.String(256), nullable=True)

    @declared_attr
    def user_id(self):
        """
        The foreign key for the user (:class:`UserModel<cornflow.models.UserModel>`).
        """
        return db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    @declared_attr
    def user(self):
        return db.relationship("UserModel")

    def __init__(self, data):
        self.user_id = data.get("user_id")
        self.data = data.get("data")
        self.data_hash = hash_json_256(self.data)
        self.name = data.get("name")
        self.description = data.get("description")
        self.schema = data.get("schema")
        self.checks = data.get("checks")
        super().__init__()

    @classmethod
    def get_all_objects(
        cls,
        schema=None,
        creation_date_gte=None,
        creation_date_lte=None,
        deletion_date_gte=None,
        deletion_date_lte=None,
        update_date_gte=None,
        update_date_lte=None,
        offset=0,
        limit=10,
        user=None,
    ):
        """
        Query to get all objects from a user

        :param UserModel user: User object.
        :param string schema: data_schema to filter (dag)
        :param string creation_date_gte: created_at needs to be larger or equal to this
        :param string creation_date_lte: created_at needs to be smaller or equal to this
        :param string deletion_date_gte: deletion_at needs to be larger or equal to this
        :param string deletion_date_lte: deletion_at needs to be smaller or equal to this
        :param string update_date_gte: update_at needs to be larger or equal to this
        :param string update_date_lte: update_at needs to be smaller or equal to this
        :param int offset: query offset for pagination
        :param int limit: query size limit
        :return: The objects
        :rtype: list(:class:`BaseDataModel`)
        """
        query = cls.query.filter(cls.deleted_at == None)
        user_access = int(current_app.config["USER_ACCESS_ALL_OBJECTS"])
        if (
            user is not None
            and not user.is_admin()
            and not user.is_service_user()
            and user_access == 0
        ):
            query = query.filter(cls.user_id == user.id)

        if schema:
            query = query.filter(cls.schema == schema)
        if creation_date_gte:
            query = query.filter(cls.created_at >= creation_date_gte)
        if creation_date_lte:
            query = query.filter(cls.created_at <= creation_date_lte)
        if deletion_date_gte:
            query = query.filter(cls.deleted_at >= deletion_date_gte)
        if deletion_date_lte:
            query = query.filter(cls.deleted_at <= deletion_date_lte)
        if update_date_gte:
            query = query.filter(cls.update_at >= update_date_gte)
        if update_date_lte:
            query = query.filter(cls.update_at <= update_date_lte)

        return query.order_by(desc(cls.created_at)).offset(offset).limit(limit).all()

    @classmethod
    def get_one_object(cls, user=None, idx=None, **kwargs):
        """
        Query to get one object from the user and the id.

        :param UserModel user: user object performing the query
        :param str or int idx: ID from the object to get
        :return: The object or None if it does not exist
        :rtype: :class:`BaseDataModel`
        """
        user_access = int(current_app.config["USER_ACCESS_ALL_OBJECTS"])
        if user is None:
            return super().get_one_object(idx=idx)
        query = cls.query.filter_by(id=idx, deleted_at=None)
        if not user.is_admin() and not user.is_service_user() and user_access == 0:
            query = query.filter_by(user_id=user.id)
        return query.first()
