"""

"""
# Partial imports

from functools import partial
from marshmallow import Schema, fields, INCLUDE

# Imports from internal modules
from cornflow_client.constants import (
    BOOLEAN_TYPE,
    STRING_TYPE,
    INTEGER_TYPE,
    FLOAT_TYPE,
    BASIC_TYPES,
)


class ParameterSchema(Schema):
    name = fields.String(required=True)
    description = fields.String(required=False)
    required = fields.Bool(default=False)
    many = fields.Bool(default=False)
    allow_none = fields.Bool(default=False)
    type = fields.String(required=True)
    valid_values = fields.List(fields.String, required=False)
    strict = fields.Bool(default=True)


def validator(valid_values, input):
    if input in valid_values:
        return True
    return False


def get_type(param_type, possible_dict=None):
    if param_type == STRING_TYPE:
        return fields.String
    if param_type == BOOLEAN_TYPE:
        return fields.Boolean
    if param_type == INTEGER_TYPE:
        return fields.Integer
    if param_type == FLOAT_TYPE:
        return fields.Float
    # we assume nested
    if possible_dict:
        return partial(fields.Nested, possible_dict[param_type])
    return None


def gen_schema(cls_name, params, possible_dict=None):
    """
    returns a marshmallow schema as if it were generated with a python object

    :param cls_name: string with the class name
    :param params: list of dictionaries
    :param possible_dict: dictionary with previously defined types
    :return:
    """
    dict_fields = {}
    # params includes at least: name, type
    for p in params:
        # p is a dictionary
        # we copy since we do not want to modify the original
        p = dict(p)
        p_type = p.pop("type")
        field_type = get_type(p_type, possible_dict=possible_dict)
        if p.get("many") and p_type in BASIC_TYPES:
            # if this is a list: we need to make an explicit list
            field_type = partial(fields.List, field_type)
        if p_type in BASIC_TYPES:
            # basic types do not support the "many" argument, apparently
            p.pop("many", None)
        valid_values = p.pop("valid_values", None)
        name = p.pop("name")
        if valid_values is not None:
            dict_fields[name] = field_type(
                validate=partial(validator, valid_values), **p
            )
        else:
            dict_fields[name] = field_type(**p)
    schema = type(cls_name, (Schema,), dict_fields)
    # HACKISH: This allows us to validate if something is missing.
    # there's probably a better way to do this:
    schema.opts.unknown = INCLUDE
    return schema


def sort_dict(dict_params):
    """
    this function returns the key, value list in an order that does not generate conflicts

    """
    backup = list(dict_params.items())
    order = dict()
    # max_count = len(order)
    count = 0
    pos = 0
    fails = 0
    check = set(BASIC_TYPES)
    while len(backup):
        key, el = backup[count]
        at_least_unseen_dependency = [ell for ell in el if ell["type"] not in check]
        if not len(at_least_unseen_dependency):
            order[key] = pos
            backup.pop(count)
            check.add(key)
            pos += 1
            fails = 0
        else:
            fails += 1
            count += 1
        if fails and fails == len(backup):
            raise ValueError(
                "sort_dict: Issue with the input dictionary."
                " There may be schemas types which are not defined"
            )
        # restart
        if count == len(backup):
            count = 0
    return order
