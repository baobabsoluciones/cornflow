""" Model for the alarms """

# Import from internal modules
from cornflow.shared import db
from cornflow.models.meta_models import TraceAttributesModel

# Imports from external libraries
from sqlalchemy.dialects.postgresql import TEXT


class AlarmsModel(TraceAttributesModel):
    """
    Model class for table alarms of the application None
    It inherits from :class:`TraceAttributesModel`
    The :class:`AlarmsModel` has the following fields:
    - **id**: number. The primary key.
    - **name**: string.
    - **criticality**: number.
    - **description**: string.
    """

    # Table name in the database
    __tablename__ = "alarms"

    # Model fields
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    name = db.Column(db.String(256), nullable=False)
    criticality = db.Column(db.Float, nullable=False)
    description = db.Column(TEXT, nullable=False)
    schema = db.Column(db.String(256), nullable=True)

    def __init__(self, data):
        super().__init__()
        self.name = data.get("name")
        self.criticality = data.get("criticality")
        self.description = data.get("description")
        self.schema = data.get("schema")

    def __repr__(self):
        """
        Method to represent the class :class:`AlarmsModel`
        :return: The representation of the :class:`AlarmsModel`
        :rtype: str
        """
        return "<Alarm " + str(self.id) + ">"

    def __str__(self):
        """
        Method to print a string representation of the class :class:`AlarmsModel`
        :return: The representation of the :class:`AlarmsModel`
        :rtype: str
        """
        return self.__repr__()