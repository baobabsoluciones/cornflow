from pytups import OrderSet


def new_set(seq):
    """
    :param seq: a (hopefully unique) list of elements (tuples, strings, etc.)
    Returns a new ordered set
    """
    return OrderSet(seq)
