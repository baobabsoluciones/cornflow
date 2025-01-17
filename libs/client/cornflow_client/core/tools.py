"""

"""

import json
import pickle

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


def as_list(x):
    """
    Transform an object into a list without nesting lists or iterating over strings.
    Behave like [x] if x is a scalar or a string and list(x) if x is another iterable.

    as_list(1) -> [1]
    as_list("one") -> ["one"]
    as_list([1,2]) -> [1,2]
    as_list({1,2}) -> [1,2]
    as_list((1,2)) -> [1,2]

    :param x: an object
    :return: a list
    """
    if isinstance(x, Iterable) and not isinstance(x, str) and not isinstance(x, dict):
        return list(x)
    else:
        return [x]