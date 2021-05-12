"""
Model for the executions
"""

# Import from libraries
import hashlib

# Imports from sqlalchemy
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import TEXT

# Imports from internal modules
from .meta_model import BaseDataModel
from ..shared.const import DEFAULT_EXECUTION_CODE, EXECUTION_STATE_MESSAGE_DICT
from ..shared.utils import db


class ExecutionModel(BaseDataModel):
    """
    Model class for the Executions.
    It inherits from :class:`BaseAttributes` to have the trace fields and user field

    The :class:`ExecutionModel` has the following fields:

    - **id**: str, the primary key for the executions, a hash generated upon creation of the execution
      and the id given back to the user.
      The hash is generated from the creation date, the user and the id of the parent instance.
    - **instance_id**: str, the foreign key for the instance (:class:`InstanceModel`). It links the execution to its
      parent instance.
    - **name**: str, the name of the execution given by the user.
    - **description**: str, the description of the execution given by the user. It is optional.
    - **config**: dict (JSON), the configuration to be used in the execution (:class:`ConfigSchema`).
    - **execution_results**: dict (JSON), the results from the execution (:class:`DataSchema`).
    - **log_text**: text, the log generated by the airflow webserver during execution. This log is stored as text.
    - **log_json**: dict (JSON), the log generated by the airflow webserver during execution.
      This log is stored as a dict (JSON).
    - **finished**: bool, if the execution has finished executing in the airflow webserver.
    - **user_id**: int, the foreign key for the user (:class:`UserModel`). It links the execution to its owner.
    - **created_at**: datetime, the datetime when the execution was created (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **updated_at**: datetime, the datetime when the execution was last updated (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **deleted_at**: datetime, the datetime when the execution was deleted (in UTC). Even though it is deleted,
      actually, it is not deleted from the database, in order to have a command that cleans up deleted data
      after a certain time of its deletion.
      This datetime is generated automatically, the user does not need to provide it.
    - **data_hash**: a hash of the data json using SHA256

    :param dict data: the parsed json got from an endpoint that contains all the required information to
      create a new execution
    """

    # Table name in the database
    __tablename__ = "executions"

    # Model fields
    id = db.Column(db.String(256), nullable=False, primary_key=True)
    instance_id = db.Column(
        db.String(256), db.ForeignKey("instances.id"), nullable=False
    )
    config = db.Column(JSON, nullable=False)
    dag_run_id = db.Column(db.String(256), nullable=True)
    dag_name = db.Column(db.String(256), nullable=True)
    log_text = db.Column(TEXT, nullable=True)
    log_json = db.Column(JSON, nullable=True)
    state = db.Column(db.SmallInteger, default=DEFAULT_EXECUTION_CODE, nullable=False)
    state_message = db.Column(
        TEXT,
        default=EXECUTION_STATE_MESSAGE_DICT[DEFAULT_EXECUTION_CODE],
        nullable=True,
    )

    def __init__(self, data):
        super().__init__(data)
        self.user_id = data.get("user_id")
        self.instance_id = data.get("instance_id")
        self.id = hashlib.sha1(
            (
                str(self.created_at)
                + " "
                + str(self.user_id)
                + " "
                + str(self.instance_id)
            ).encode()
        ).hexdigest()

        self.dag_run_id = data.get("dag_run_id")
        self.dag_name = data.get("dag_name")
        self.state = data.get("state", DEFAULT_EXECUTION_CODE)
        self.state_message = EXECUTION_STATE_MESSAGE_DICT[self.state]
        self.config = data.get("config")
        self.log_text = data.get("log_text")
        self.log_json = data.get("log_json")

    def save(self):
        """
        Saves the execution to the database
        """
        db.session.add(self)
        db.session.commit()

    def update(self, data):
        """
        Updates the execution in the data base and automatically updates the updated_at field

        :param dict data:  A dictionary containing the updated data for the execution
        """
        for key, item in data.items():
            setattr(self, key, item)
        super().update(data)

    def delete(self):
        """
        Deletes an execution permanently from the data base
        """
        db.session.delete(self)
        db.session.commit()

    def update_state(self, code):
        """
        Method to update the state code and message of an execution

        :param int code: State code for the execution
        :return: nothing
        """
        self.state = code
        self.state_message = EXECUTION_STATE_MESSAGE_DICT[code]
        super().update({})

    @staticmethod
    def get_one_execution_from_id_admin(idx):
        """
        Query to get one execution with the given id
        BEWARE: this should only be called from the admin user

        :param str idx: Execution ID
        :return: The execution.
        """
        return ExecutionModel.query.filter_by(id=idx, deleted_at=None).first()

    def __repr__(self):
        """
        Method to represent the class :class:`ExecutionModel`

        :return: The representation of the :class:`ExecutionModel`
        :rtype: str
        """
        return "<id {}>".format(self.id)

    def __str__(self):
        """
        Method to print a string representation of the :class:`ExecutionModel`

        :return: The string for the :class:`ExecutionModel`
        :rtype: str
        """
        return "<id {}>".format(self.id)
