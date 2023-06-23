""" Model for the alarms """

# Import from internal modules
from cornflow.shared import db
from cornflow.models.meta_models import TraceAttributesModel


# Imports from external libraries
from sqlalchemy.dialects.postgresql import TEXT
from typing import Optional


class MainAlarmsModel(TraceAttributesModel):
    """
    Model class for table main_alarms of the application None
    It inherits from :class:`TraceAttributesModel`
    The :class:`MainAlarmsModel` has the following fields:
    - **id**: number. The primary key.
    - **id_alarm**: integer.
    - **criticality**: number.
    - **message**: string.
    """

    # Table name in the database
    __tablename__ = "main_alarms"

    # Model fields
    id: db.Mapped[int] = db.mapped_column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    id_alarm: db.Mapped[int] = db.mapped_column(db.Integer, db.ForeignKey("alarms.id"), nullable=False)
    criticality: db.Mapped[float] = db.mapped_column(db.Float, nullable=False)
    message: db.Mapped[str] = db.mapped_column(TEXT, nullable=False)
    schema: db.Mapped[Optional[str]] = db.mapped_column(db.String(256), nullable=True)

    def __init__(self, data):
        super().__init__()
        self.id_alarm = data.get("id_alarm")
        self.criticality = data.get("criticality")
        self.message = data.get("message")
        self.schema = data.get("schema")

    def __repr__(self):
        """
        Method to represent the class :class:`MainAlarmsModel`
        :return: The representation of the :class:`MainAlarmsModel`
        :rtype: str
        """
        return "<Main_Alarms " + str(self.id) + ">"

    def __str__(self):
        """
        Method to print a string representation of the class :class:`MainAlarmsModel`
        :return: The representation of the :class:`MainAlarmsModel`
        :rtype: str
        """
        return self.__repr__()