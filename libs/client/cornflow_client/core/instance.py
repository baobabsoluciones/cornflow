"""

"""

from abc import ABC, abstractmethod

from jsonschema import Draft7Validator

from cornflow_client.constants import BadInstanceChecks

from .instance_solution import InstanceSolutionCore


class InstanceCore(InstanceSolutionCore, ABC):
    """
    The instance template.
    """

    def data_checks(self) -> dict:
        """
        Method that executes the InstanceCore.check() method and validates the result against the schema_checks

        :return: The dictionary returned by the InstanceCore.check() method
        :rtype: dict
        :raises BadInstanceChecks: if the instance checks do not match the schema
        :author: baobab soluciones
        """
        checks = self.check()
        validator = Draft7Validator(self.schema_checks)
        if not validator.is_valid(checks):
            raise BadInstanceChecks(
                f"The instance checks do not match the schema: {[e for e in validator.iter_errors(checks)]}"
            )
        return checks

    @abstractmethod
    def check(self) -> dict:
        """
        Method that checks if there are inconsistencies in the data of the instance and if the problem is feasible

        :return: An dictionary containing the inconsistencies found and indicating if the problem is infeasible
        """
        return dict()

    @property
    @abstractmethod
    def schema_checks(self) -> dict:
        """
        A dictionary representation of the json-schema for the dictionary returned by the method Instance.check()
        """
        raise NotImplementedError()
