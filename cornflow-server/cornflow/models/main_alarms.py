""" Model for the alarms """

# Import from internal modules
from cornflow.shared import db
from cornflow.models.meta_models import TraceAttributesModel


# Imports from external libraries
from sqlalchemy.dialects.postgresql import TEXT


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
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    id_alarm = db.Column(db.Integer, db.ForeignKey("alarms.id"), nullable=False)
    criticality = db.Column(db.Float, nullable=False)
    message = db.Column(TEXT, nullable=False)
    schema = db.Column(db.String(256), nullable=True)

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