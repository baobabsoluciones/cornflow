
from cornflow_core.resources import BaseMetaResource
from cornflow.models import InstanceModel, ExecutionModel
from ..tools.cornflow_tools import put_model_data, post_model_data, launch_dag


class SolveEndpoint(BaseMetaResource):
    """
    Endpoint used to launch a resolution with the following steps:
    - create an instance and post it.
    - create an execution related to the instance and post it.
    - Launch the dag in Airflow in order to solve the execution.

    Available methods: [post]
    Endpoint used by: the user interface.
    """

    def __init__(self):
        super().__init__()

    def post(self, **kwargs):
        raise NotImplementedError("post method should be implemented")


    def post_instance(self, data, instance_name, instance_description):
        """
        Post a new instance in instances table.

        :param data: the instance data.
        :param instance_name: name of the instance.
        :param instance_description: description of the instance.
        :return: instance data and status code.
        """
        instance_content = dict(
            name=instance_name, description=instance_description, data=data
        )
        return self.post_list(data=instance_content)

    def post_execution(
            self, instance_id, config, schema, execution_name, execution_description
    ):
        """
        Post a new execution in executions table.

        :param instance_id: id of the instance.
        :param config: config dict.
        :param schema: name fo the associated dag.
        :param execution_name: name of the execution.
        :param execution_description: description of the execution.
        :return: execution data and status code.
        """

        execution_content = dict(
            name=execution_name,
            description=execution_description,
            instance_id=instance_id,
            config=config,
            schema=schema,
        )
        execution, status_code = post_model_data(
            execution_content, data_model=ExecutionModel, user_id=self.get_user_id()
        )
        # Quick fix to add id_execution to config
        execution_content["config"]["id_execution"] = execution.id
        execution, status = put_model_data(
            execution_content, ExecutionModel, idx=execution.id
        )
        return execution, status_code

    def check_instance(self, data, stop_if_empty):
        """
        The model should not be able to work if some tables are empty.

        :param data: data of the instance.
        :param stop_if_empty: list of tables to check
        :return: True if the instance is fine, False if some tables are missing.
        """
        empty_tables = [
            table
            for table in stop_if_empty
            if table not in data or len(data[table]) == 0
        ]

        return len(empty_tables) > 0

    def solve(self, execution):
        """
        Launch the dag to solve the execution.

        :param execution: the execution data.
        :return: executiond data and success code
        """
        return launch_dag(execution, user_id=self.get_user_id())