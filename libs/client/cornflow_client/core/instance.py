"""

"""
# Partial imports
from abc import ABC, abstractmethod

# Imports from internal modules
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
