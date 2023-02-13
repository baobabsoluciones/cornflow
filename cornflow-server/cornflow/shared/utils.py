"""

"""
import hashlib
from importlib import import_module
import json
import os
import sys
from sqlalchemy.dialects.postgresql import TEXT
from cornflow_core.models import EmptyBaseModel
from cornflow_core.shared import db
from sqlalchemy.sql.sqltypes import Integer


def hash_json_256(data):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _import_file(filename):
    return import_module(filename)


def import_models(models_paths):
    if not isinstance(models_paths, list):
        models_paths = [models_paths]

    for path in models_paths:
        sys.path.append(path)
        files = os.listdir(path)
        # we go file by file and try to import it if matches the filters
        for dag_module in files:
            filename, ext = os.path.splitext(dag_module)
            if ext not in [".py", ""]:
                continue
            try:
                _import_file(filename)
            except Exception as e:
                continue


def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])


type_converter = {
    db.String: False,
    TEXT: False,
    Integer: True,
    db.Integer: True,
    db.SmallInteger: True,
}


def get_all_tables(models_paths):
    import_models(models_paths)
    models = all_subclasses(EmptyBaseModel)
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
