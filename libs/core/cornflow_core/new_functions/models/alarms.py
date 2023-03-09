# Import from libraries
from cornflow_core.shared import db
from cornflow_core.models import TraceAttributesModel
from sqlalchemy.dialects.postgresql import ARRAY


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
    id = db.Column(db.Float, nullable=False, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    criticality = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(256), nullable=False)

    def __init__(self, data):
        super().__init__()
        self.id = data.get("id")
        self.name = data.get("name")
        self.criticality = data.get("criticality")
        self.description = data.get("description")

    def __repr__(self):
        """
        Method to represent the class :class:`AlarmsModel`

        :return: The representation of the :class:`AlarmsModel`
        :rtype: str
        """
        return "<Alarms " + str(self.id) + ">"

    def __str__(self):
        """
        Method to print a string representation of the class :class:`AlarmsModel`

        :return: The representation of the :class:`AlarmsModel`
        :rtype: str
        """
        return self.__repr__()
