"""
Model for the reports
"""

# Import from libraries
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.ext.declarative import declared_attr

# Imports from internal modules
from cornflow.models.base_data_model import TraceAttributesModel
from cornflow.shared import db


class ReportModel(TraceAttributesModel):
    """
    Model class for the Reports.
    It inherits from :class:`TraceAttributesModel<cornflow.models.base_data_model.TraceAttributesModel>` to have the trace fields and user field.

    - **id**: int, the report id, primary key for the reports.
    - **execution_id**: str, the foreign key for the execution (:class:`ExecutionModel`). It links the report to its
      parent execution.
    - **file_url**: str, the link with the actual report. It should be a valid url to a cloud storage bucket or a file.
    - **name**: str, the name of the report given by the user.
    - **description**: str, the description of the report given by the user. It is optional.
    - **user_id**: int, the foreign key for the user (:class:`UserModel`). It links the report to its owner.
    - **created_at**: datetime, the datetime when the report was created (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **updated_at**: datetime, the datetime when the report was last updated (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **deleted_at**: datetime, the datetime when the report was deleted (in UTC). Even though it is deleted,
      actually, it is not deleted from the database, in order to have a command that cleans up deleted data
      after a certain time of its deletion.
      This datetime is generated automatically, the user does not need to provide it.

    """

    # Table name in the database
    __tablename__ = "reports"

    # Model fields
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    execution_id = db.Column(
        db.String(256), db.ForeignKey("executions.id"), nullable=False
    )
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(TEXT, nullable=True)
    file_url = db.Column(db.String(256), nullable=False)

    @declared_attr
    def user_id(self):
        """
        The foreign key for the user (:class:`UserModel<cornflow.models.UserModel>`).
        """
        return db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    @declared_attr
    def user(self):
        return db.relationship("UserModel")

    def __init__(self, data: dict):
        super().__init__()
        self.user_id = data.get("user_id")
        self.execution_id = data.get("execution_id")
        self.name = data.get("name")
        self.description = data.get("description")
        self.file_url = data.get("file_url")

    def update(self, data):
        """
        Method used to update a report from the database

        :param dict data: the data of the object
        :return: None
        :rtype: None
        """
        super().update(data)

    def update_link(self, file_url: str):
        """
        Method to update the report link

        :param str file_url: new URL for the report
        :return: nothing
        """
        self.file_url = file_url
        super().update({})

    def __repr__(self):
        """
        Method to represent the class :class:`ReportModel`

        :return: The representation of the :class:`ReportModel`
        :rtype: str
        """
        return f"<Report {self.id}>"

    def __str__(self):
        """
        Method to print a string representation of the :class:`ReportModel`

        :return: The string for the :class:`ReportModel`
        :rtype: str
        """
        return self.__repr__()
