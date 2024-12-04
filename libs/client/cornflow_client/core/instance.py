"""

"""

from abc import ABC, abstractmethod
from typing import List

from jsonschema import Draft7Validator

from .instance_solution import InstanceSolutionCore


class InstanceCore(InstanceSolutionCore, ABC):
    """
    The instance template.
    """

    # TODO: make abstractmethod
    def check(self, *args, **kwargs) -> dict:
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

    def validate_checks(self, checks: dict) -> List:
        """
        Validate the check of the instance against its json schema

        :param dict checks: the dictionary returned by the method InstanceCore.check()
        :return: a list of errors
        :rtype: List[jsonschema.exceptions.ValidationError]
        """
        validator = Draft7Validator(self.schema_checks)
        if not validator.is_valid(checks):
            return [e for e in validator.iter_errors(checks)]
        return []
