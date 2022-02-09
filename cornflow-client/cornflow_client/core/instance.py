"""

"""
# Partial imports
from abc import ABC

# Imports from internal modules
from .instance_solution import InstanceSolutionCore


class InstanceCore(InstanceSolutionCore, ABC):
    """
    The instance template.
    """

    # TODO: make abstractmethod
    def check_inconsistencies(self, *args, **kwargs) -> dict:
        """
        Method that checks if there are inconsistencies in the data of the current instance.

        :return: A dictionary containing the inconsistencies found.
        """
        return dict()

    # TODO: make abstractmethod
    def check_feasibility(self, *args, **kwargs) -> bool:
        """
        Method that checks if the problem is feasible.

        :return: True if the problem is feasible, False otherwise
        """
        return True

    # TODO: make abstractmethod
    def check(self, *args, **kwargs) -> dict:
        """
        Method that checks if there are inconsistencies in the data of the instance and if the problem is feasible

        :return: An dictionary containing the inconsistencies found and indicating if the problem is infeasible
        """
        inconsistencies = self.check_inconsistencies(*args, **kwargs)
        is_feasible = self.check_feasibility(*args, **kwargs)
        if not is_feasible:
            inconsistencies["is_infeasible"] = True
        return inconsistencies
