""" """

from flask import current_app
from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.ext.declarative import declared_attr

from cornflow.models.meta_models import TraceAttributesModel
from cornflow.shared import db
from cornflow.shared.const import USER_ACCESS_ALL_OBJECTS_NO
from cornflow.shared.utils import hash_json_256


def _hide_platform_objects(query, cls, user):
    """
    Keeps the data owned by internal (platform) users out of the sight of
    client users.

    Objects created by a user holding a platform role (platform_admin,
    platform_viewer, platform_planner) are only visible to platform users. So
    on a shared or staging deployment the test data an operator creates never
    shows up for a client user — not even for a client admin, who otherwise
    sees every object of the deployment.

    The reverse is not restricted: platform users are the operators and keep
    the visibility their role grants them.

    :param query: the query being built
    :param cls: the model class being queried
    :param user: the user performing the query (may be None for internal calls)
    :return: the query, filtered when applicable
    """
    if user is None:
        return query
    if not int(current_app.config.get("PLATFORM_DATA_ISOLATION", 1)):
        return query
    # Imported here to avoid a circular import at module load
    from cornflow.models.user_role import UserRoleModel

    if UserRoleModel.is_platform_user(user.id):
        return query
    # The platform users are the internal operators: a handful of rows, so
    # the id list is materialised instead of correlating a subquery (keeps the
    # filter portable across SQLAlchemy versions).
    platform_user_ids = UserRoleModel.get_platform_user_ids()
    if not platform_user_ids:
        return query
    return query.filter(
        db.or_(
            cls.user_id.is_(None),
            ~cls.user_id.in_(platform_user_ids),
        )
    )


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
        options=None,
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
        :param list options: extra SQLAlchemy loader options (e.g. defer()) to apply to the query
        :return: The objects
        :rtype: list(:class:`BaseDataModel`)
        """
        query = cls.query.filter(cls.deleted_at == None)
        if options:
            query = query.options(*options)
        user_access = int(current_app.config["USER_ACCESS_ALL_OBJECTS"])
        if (
            user is not None
            and not user.is_admin()
            and not user.is_service_user()
            and user_access == 0
        ):
            query = query.filter(cls.user_id == user.id)

        # Client users never see the objects of internal (platform) users
        query = _hide_platform_objects(query, cls, user)

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
    def get_one_object(cls, user=None, idx=None, options=None, **kwargs):
        """
        Query to get one object from the user and the id.

        :param UserModel user: user object performing the query
        :param str or int idx: ID from the object to get
        :param list options: extra SQLAlchemy loader options (e.g. defer()) to apply to the query
        :return: The object or None if it does not exist
        :rtype: :class:`BaseDataModel`
        """
        user_access = int(current_app.config["USER_ACCESS_ALL_OBJECTS"])
        if user is None:
            return super().get_one_object(idx=idx)
        query = cls.query
        if options:
            query = query.options(*options)
        query = query.filter_by(id=idx, deleted_at=None)
        if not user.is_admin() and not user.is_service_user() and user_access == USER_ACCESS_ALL_OBJECTS_NO:
            query = query.filter_by(user_id=user.id)
        # Client users never see the objects of internal (platform) users
        query = _hide_platform_objects(query, cls, user)
        return query.first()
