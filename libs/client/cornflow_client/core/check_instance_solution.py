from .tools import as_list


class CheckInstanceSolution:

    # this should be set depending on the project
    default_message = "Problem detected: {}"
    default_id_alarm = 1
    default_criticality = 2

    def __init__(self, instance, solution=None, logger=None):
        self.inst = instance
        self.sol = solution
        self.logger = logger
        self.checks = {}

    def get_all_checks(self):
        """
        Finds all class methods starting with check_ and returns them in a list.
        :return: A list of check methods.
        """
        lst = [
            m
            for m in dir(self)
            if m.startswith("check_") and callable(getattr(self, m))
        ]
        return lst

    def launch_all_checks(self):
        """
        Launch every check method and save the results in a dict self.checks.
        The check functions are expected to return a dict with the following keys:
            - id_alarm: the id of the alarm type in the database.
            - data: data of the check (empty if ok).
            - msg_args: list of arguments of the alarm message.
            - check_ok: True if the check passed.
            - criticality: criticality of the alarm.

        :return: True if all checks passed and false otherwise
        """
        self.checks = {m: getattr(self, m)() for m in self.get_all_checks()}
        self.create_all_alarms()
        return self.all_checks_ok()

    def all_checks_ok(self):
        """
        calculate if all checks have passed.

        :return: True if all checks passed and false otherwise.
        """
        return all(v["check_ok"] for v in self.checks.values())

    def create_all_alarms(self):
        """
        Create alarm for every check that failed.

        :return: true
        """
        for name, check in self.checks.items():
            if not check["check_ok"]:
                id_alarm = check.get("id_alarm", self.default_id_alarm)
                criticality = check.get("criticality", self.default_criticality)
                self.create_alarm(id_alarm, check["msg_args"], criticality=criticality)
        return True

    def create_alarm(self, msg_args):
        """
        Create an alarm for failed checks.
        If the app is not connected to cornflow, then generate warnings

        :param id_alarm: id of the alarm
        :param msg_args: message of the alarm
        :param criticality: criticality of the alarm.
        :return: None
        """
        msg = self.default_message.format(*as_list(msg_args))
        self.logger.warning(msg)
