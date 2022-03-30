from pytups import SuperDict, TupList
import numpy as np
import pickle


def get_drivers(jsonschema_dict):
    # master table
    drivers = _index(jsonschema_dict["drivers"])

    # drivers amd time windows
    tw_drivers = index_list(
        jsonschema_dict["driversTimeWindows"], "id_driver", ["start", "end"]
    )
    assign_list_prop(drivers, "timewindows", tw_drivers)

    # drivers and their trailers
    driver_trailers = TupList(jsonschema_dict["driversTrailers"]).to_dict(
        result_col="id_trailer", indices=["id_driver"]
    )
    assign_list_prop(drivers, "trailer", driver_trailers)
    return drivers


def get_sources(jsonschema_dict):
    # master table
    sources = _index(jsonschema_dict["sources"])
    # locations and their trailers
    loc_trailers = TupList(jsonschema_dict["allowedTrailers"]).to_dict(
        result_col="id_trailer", indices=["id_location"]
    )
    assign_list_prop(sources, "allowedTrailers", loc_trailers)
    return sources


def get_customers(jsonschema_dict):
    # master table
    customers = _index(jsonschema_dict["customers"])
    # customers, time windows and orders
    tw_customers = index_list(
        jsonschema_dict["customersTimeWindows"], "id_customer", ["start", "end"]
    )
    ord_customers = index_list(
        jsonschema_dict["orders"],
        "id_customer",
        ["earliestTime", "latestTime", "orderQuantityFlexibility", "Quantity"],
    )
    loc_trailers = TupList(jsonschema_dict["allowedTrailers"]).to_dict(
        result_col="id_trailer", indices=["id_location"]
    )
    assign_list_prop(customers, "timewindows", tw_customers)
    assign_list_prop(customers, "orders", ord_customers)
    assign_list_prop(customers, "allowedTrailers", loc_trailers)

    # customer forecasts
    # we assume forecasts don't have a number for each period
    forecasts = (
        TupList(jsonschema_dict["forecasts"])
        .take(["id_customer", "time", "forecast"])
        .vfilter(lambda v: v[2] > 0)
    )
    horizon = jsonschema_dict["parameters"]["horizon"]
    for k, v in customers.items():
        v["Forecast"] = TupList(np.zeros(horizon))
    for _id, time, quantity in forecasts:
        # we have more periods than needed, apparently
        if time >= len(customers[_id]["Forecast"]):
            continue
        customers[_id]["Forecast"][time] += quantity

    return customers


def get_matrices_from_file(data_from_file):
    def matrix_to_dict(matrix, key, func):
        matrix = TupList(matrix).vapply(lambda v: v[key])
        result = SuperDict()
        for L1, row in enumerate(matrix):
            for L2, col in enumerate(row):
                result[L1, L2] = func(col)
        return result

    times = matrix_to_dict(data_from_file["timeMatrices"]["ArrayOfInt"], "int", int)
    distances = matrix_to_dict(
        data_from_file["DistMatrices"]["ArrayOfDouble"], "double", float
    )
    return times.kvapply(
        lambda k, v: SuperDict(time=v, dist=distances[k], L1=k[0], L2=k[1])
    )


def get_drivers_from_file(data_from_file):
    drivers = from_element_or_list_to_dict(
        data_from_file["drivers"]["IRP_Roadef_Challenge_Instance_driver"]
    )
    for driver in drivers.keys():
        drivers[driver]["timewindows"] = el_to_list(
            drivers, driver, "timewindows", "TimeWindow"
        )
        drivers[driver]["trailer"] = el_to_list(drivers, driver, "trailer", "int")
    return drivers


def get_trailers_from_file(data_from_file):
    return from_element_or_list_to_dict(
        data_from_file["trailers"]["IRP_Roadef_Challenge_Instance_Trailers"]
    )


def get_bases_from_file(data_from_file):
    return dict(index=int(data_from_file["bases"]["index"]))


def get_sources_from_file(data_from_file):
    sources = from_element_or_list_to_dict(
        data_from_file["sources"]["IRP_Roadef_Challenge_Instance_Sources"]
    )
    for source in sources.keys():
        sources[source]["allowedTrailers"] = el_to_list(
            sources, source, "allowedTrailers", "int"
        )
    return sources


def get_customers_from_file(data_from_file):
    customers = from_element_or_list_to_dict(
        data_from_file["customers"]["IRP_Roadef_Challenge_Instance_Customers"]
    )
    for customer in customers.keys():
        customers[customer]["allowedTrailers"] = el_to_list(
            customers, customer, "allowedTrailers", "int"
        )
        customers[customer]["timewindows"] = el_to_list(
            customers, customer, "timewindows", "TimeWindow"
        )
        customers[customer]["Forecast"] = customers[customer]["Forecast"]["double"]
        customers[customer]["orders"] = el_to_list(
            customers, customer, "order", "Order"
        )
    return customers


def el_to_list(data, key1, key2, key3):
    """
    Extracts a value from the third layer of a dictionary given the
    three keys and converts it to a list if it is not a list
    """
    val = data[key1].get(key2, dict()).get(key3, [])
    if isinstance(val, list):
        return val
    else:
        return [val]


def assign_list_prop(table: dict, property: str, obj: dict):
    for k, v in table.items():
        v[property] = obj.get(k, [])


def _index(table):
    return SuperDict({el["index"]: SuperDict(el) for el in table})


def index_list(table, index, _list):
    """
    indexes the table by index and returns a dictionary with _list keys
    """
    return (
        TupList(table)
        .to_dict(result_col=_list, indices=[index])
        .vapply(lambda v: v.vapply(lambda vv: SuperDict(zip(_list, vv))))
    )


def drivers_to_jsonschema(drivers_data: SuperDict):
    driversTimeWindows = [
        dict(id_driver=key, **tw)
        for key, time_windows in drivers_data.get_property("timewindows").items()
        for tw in time_windows
    ]

    driversTrailers = [
        SuperDict(id_driver=key, id_trailer=trailer)
        for key, trailers in drivers_data.get_property("trailer").items()
        for trailer in trailers
    ]
    drivers = drop_props_get_values(drivers_data, ["trailer", "timewindows"])
    return SuperDict(
        drivers=drivers,
        driversTrailers=driversTrailers,
        driversTimeWindows=driversTimeWindows,
    )


def customers_to_jsonschema(customers_data: SuperDict):
    customersTimeWindows = [
        SuperDict(id_customer=key, **tw)
        for key, time_windows in customers_data.get_property("timewindows").items()
        for tw in time_windows
    ]

    orders = [
        SuperDict(id_customer=key, **order)
        for key, orders in customers_data.get_property("orders").items()
        for order in orders
    ]

    forecasts = [
        SuperDict(id_customer=key, time=time, forecast=forecast)
        for key, forecasts in customers_data.get_property("Forecast").items()
        for time, forecast in enumerate(forecasts)
        if forecast > 0
    ]

    allowedTrailers = [
        SuperDict(id_location=key, id_trailer=id_trailer)
        for key, trailers in customers_data.get_property("allowedTrailers").items()
        for id_trailer in trailers
    ]
    customers = drop_props_get_values(
        customers_data, ["timewindows", "Forecast", "allowedTrailers", "orders"]
    )
    return SuperDict(
        customers=customers,
        customersTimeWindows=customersTimeWindows,
        orders=orders,
        forecasts=forecasts,
        allowedTrailers=allowedTrailers,
    )


def sources_to_jsonschema(sources_data):

    allowedTrailers = [
        SuperDict(id_location=key, id_trailer=id_trailer)
        for key, trailers in sources_data.get_property("allowedTrailers").items()
        for id_trailer in trailers
    ]

    sources = drop_props_get_values(sources_data, ["allowedTrailers"])
    return SuperDict(sources=sources, allowedTrailers=allowedTrailers)


def drop_props_get_values(dictionary: SuperDict, props: list):
    return dictionary.vapply(lambda v: v.kfilter(lambda k: k not in props)).values_tl()


def from_element_or_list_to_dict(element_or_list):
    if not isinstance(element_or_list, list):
        element_or_list = [element_or_list]
    return {int(el["index"]): el for el in element_or_list}


def copy(dictionary):
    return pickle.loads(pickle.dumps(dictionary, -1))
