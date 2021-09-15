from pytups import OrderSet
import json


def new_set(seq):
    """
    :param seq: a (hopefully unique) list of elements (tuples, strings, etc.)
    Returns a new ordered set
    """
    return OrderSet(seq)


def load_json(path):
    with open(path) as json_file:
        file = json.load(json_file)
    return file


def save_json(data, path):
    with open(path, "w") as outfile:
        json.dump(data, outfile)
