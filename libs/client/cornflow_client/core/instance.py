""" """

from abc import ABC, abstractmethod
from typing import List, Dict, Union

from jsonschema import Draft7Validator

from cornflow_client.constants import BadInstanceChecks
from .instance_solution import InstanceSolutionCore


class InstanceCore(InstanceSolutionCore, ABC):
    """
    The instance template.
    """

    def data_checks(self) -> dict:
        """
        Method that executes the InstanceCore.check() method and validates the result
        against the schema_checks

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

    def check(self) -> dict:
        """
        Method that checks if there are inconsistencies in the data of the instance and
        if the problem is feasible

        This method can be overridden if necessary

        :return: An dictionary containing the inconsistencies found and indicating if
        the problem is infeasible
        """
        return self.launch_all_checks()

    @property
    @abstractmethod
    def schema_checks(self) -> dict:
        """
        A dictionary representation of the json-schema for the dictionary returned by
        the method Instance.check()
        """
        raise NotImplementedError()

    def get_check_methods(self) -> list:
        """
        Finds all class methods starting with check_ and returns them in a list.

        :return: A list of check methods.
        """
        check_methods = [
            m
            for m in dir(self)
            if m.startswith("check_")
            and callable(getattr(self, m))
            and m != "check_schema"
        ]
        return check_methods

    def launch_all_checks(self) -> Dict[str, Union[List, Dict]]:
        """
        Launch every check method and return a dict with the check method name as key
        and the list/dict of errors / warnings as value.

        It will only return those checks that return a non-empty list/dict.
        If a check method raises an exception, it will be caught and a generic error
        message will be added to the checks dictionary.
        """
        check_method_names = self.get_check_methods()
        check_methods = {}

        # Execute each check method and catch any exceptions
        for method_name in check_method_names:
            try:
                check_methods[method_name] = getattr(self, method_name)()
            except Exception:
                # If a check fails, add a generic error message
                check_methods[method_name] = [
                    {
                        "error_type": "Check execution error",
                        "error_message": "The execution of the check has failed, please contact support",
                    }
                ]

        failed_checks = {}
        for k, v in check_methods.items():
            if v is None:
                continue

            try:
                if len(v) > 0:
                    failed_checks[k.split("check_")[1]] = v
            except TypeError:
                failed_checks[k.split("check_")[1]] = v

        return dict(failed_checks)
