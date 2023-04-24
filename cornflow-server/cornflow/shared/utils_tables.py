# Imports from external libraries
import inspect
import os
import sys

from importlib import import_module
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.sql.sqltypes import Integer

# Imports from internal modules
from cornflow.models import *
from cornflow.models.meta_models import EmptyBaseModel
from cornflow.shared import db


def _import_file(filename):
    return import_module(filename)


def import_models():
    external_app = int(os.getenv("EXTERNAL_APP", 0))
    if external_app != 0:
        sys.path.append("./")
        external_app_module = os.getenv("EXTERNAL_APP_MODULE")

        external_module = import_module(external_app_module)
        models = external_module.models

        return [md for md in models.__dict__.values() if inspect.isclass(md)]
    return None


def all_subclasses(cls, models=None):
    subclasses = set()
    if models is not None:
        for val in models:
            if issubclass(val, cls):
                subclasses.add(val)

    return subclasses.union(set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)]))


type_converter = {
    db.String: False,
    TEXT: False,
    Integer: True,
    db.Integer: True,
    db.SmallInteger: True,
}


def get_all_tables():
    external_apps_models = import_models()
    models = all_subclasses(EmptyBaseModel, external_apps_models)
    tables = dict()
    for model in models:
        try:
            tables[model.__tablename__] = {"model": model, "convert_id": False}
            props = {
                col.__dict__["key"]: next(iter(col.proxy_set))
                for col in model.__dict__["__table__"]._columns
            }
            for typeclass, convert_to_int in type_converter.items():
                if isinstance(props["id"].type, typeclass):
                    tables[model.__tablename__]["convert_id"] = convert_to_int
                    break
        except AttributeError:
            pass
    return tables


def item_as_dict(item):
    return {c.name: getattr(item, c.name) for c in item.__table__.columns}


def items_as_dict_list(ls):
    return [
        {c.name: getattr(item, c.name) for c in item.__table__.columns}
        for item in ls
    ]