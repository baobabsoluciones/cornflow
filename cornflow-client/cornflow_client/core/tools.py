"""

"""
# Full imports
import json
import pickle

# Partial imports
from pytups import OrderSet


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


def copy(dictionary):
    return pickle.loads(pickle.dumps(dictionary, -1))
