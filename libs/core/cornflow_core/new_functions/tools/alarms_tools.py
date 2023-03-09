from cornflow.shared.const import EXEC_STATE_ERROR_START
from cornflow_core.exceptions import InvalidData

from msc.models import AlarmsModel, MainAlarmsModel
from msc.schemas import AlarmsResponse, MainAlarmsResponse
from msc.temp.cornflow_tools import post_model_data


def create_alarm(
    id_alarm,
    message_args,
    criticality,
    user_id,
    raise_error=False,
    alarm_model=MainAlarmsModel,
    **kwargs
):
    """
    Create an alarm in the table main_alarm.

    :param id_alarm: id of the type of alarm.
    :param message_args: arguments for the message.
    :param criticality: level of criticality of the alarm.
    :param user_id: user id
    :param raise_error: True if cornflow should raise an error and cancel the resolution.
    :param alarm_model: model of the table where to create the alarm.
    :param kwargs: other keyword arguments to use to create the alarm.
    :return: the message
    """
    # Get alarm master
    query = AlarmsModel.get_one_object(idx=id_alarm)
    alarms_message = AlarmsResponse().dump(query)
    message_args = AlarmsModel.as_list(message_args)
    message = alarms_message["description"].format(*message_args)
    # Create alarm
    new_alarm_content = dict(
        id_alarm=id_alarm, message=message, criticality=criticality, **kwargs
    )
    post_model_data(new_alarm_content, alarm_model, user_id=user_id)
    if raise_error:
        raise InvalidData(
            error="Resolution cancelled",
            payload=dict(message=message, state=EXEC_STATE_ERROR_START),
            status_code=400,
        )
    return message


def delete_alarms(alarm_model=MainAlarmsModel, **kwargs):
    """
    Delete (disable) old alarms from the table power_plant_alarms for a given power_plant.

    :param alarm_model: model of the table where to create the alarm.
    :param kwargs: other keyword arguments to use to create the alarm.
    :return: None
    """
    query = alarm_model.get_all_objects(**kwargs).all()
    for item in query:
        item.disable()
    return None


def get_active_alarms(alarm_model=MainAlarmsModel, alarm_schema=MainAlarmsResponse, filter=None, filter_by=None):
    # Read all alarms
    query = (
        alarm_model.query.filter(alarm_model.deleted_at == None)
        .filter_by(**filter_by)
        .filter(*filter)
        .all()
    )
    return alarm_schema().dump(query, many=True)


def create_resolution_alarms(active_alarms, alarm_types, user_id, max_show=4, high_criticality=1):
    """
    When creating a new instance to solve, create a new alarm to sum up all active alarms.

    :param active_alarms: list of active alarms
    :param alarm_types: dict of alarm types to generate in the format {id_alarm:crit_level}
    :param user_id: id of the user
    :param max_show: maximum number fo alarms to show in the message.
    :param high_criticality: level of high criticality
    :return: None
    """
    for id_alarm, crit in alarm_types.items():
        crit_alarms = [a for a in active_alarms if a["criticality"] == crit]
        n_alarms = len(crit_alarms)
        max_show = min(n_alarms, max_show)
        message = ", ".join(a["name"] for a in crit_alarms[:max_show])
        while len(message) > 220:
            max_show -= 1
            message = ", ".join(a["name"] for a in crit_alarms[:max_show])
        if n_alarms > max_show:
            message += f" y {n_alarms - max_show} otras alarmas."
        else:
            message +="."

        if n_alarms > 0:
            create_alarm(
                id_alarm,
                message_args=(n_alarms, message),
                criticality=crit,
                raise_error=(crit <= high_criticality),
                user_id=user_id,
            )