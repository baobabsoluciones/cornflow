# Import from libraries
import os
import re
import sys
import json
import importlib.util
from distutils.dir_util import copy_tree
from unittest.mock import MagicMock
from flask_sqlalchemy import SQLAlchemy
import shutil
from pytups import TupList, SuperDict
from sqlalchemy.dialects.postgresql import TEXT, JSON


class SchemaGenerator:
    def __init__(self, path, output_path=None, ignore_files=None):
        self.path = path
        self.tmp_path = os.path.join(os.getcwd(), 'tmp_files')
        self.output_path = output_path or './output_schema.json'
        self.ignore_files = ignore_files or []
        self.parents = dict()
        self.data = dict()
        self.model_table = dict()
        self.table_model = dict()

    def main(self):
        copy_tree(self.path, self.tmp_path)
        files = (
            TupList(os.listdir(self.tmp_path))
            .vfilter(lambda v: v != '__init__.py' and v != '__pycache__' and v not in self.ignore_files)
            .vapply(lambda v: (os.path.join(self.tmp_path, v), v[:-3]))
        )
        self.mock_packages(files)
        self.parse(files)
        self.inherit()
        schema = self.to_schema()
        with open(self.output_path, 'w') as fd:
            json.dump(schema, fd, sort_keys=True, indent=2)
        self.clear()

    def mock_packages(self, files):
        # Mocking all relative imports
        for file_path, file_name in files:
            with open(file_path, 'r') as fd:
                text = fd.read()
            parents = re.findall(r'class (.+)\((.+)\):', text)
            for cl, parent in parents:
                self.parents[cl] = parent.replace(' ', '')
            libs = re.findall(r'from ((\.+\w+)+) import (\w+)', text)
            for lib in libs:
                text = text.replace(lib[0], 'mockedpackage')
            with open(file_path, 'w') as fd:
                fd.write(text)

        mymodule = MagicMock()
        db = SQLAlchemy()
        mymodule.db.Column = db.Column
        mymodule.db.String.return_value = 'string'
        mymodule.db.Integer = 'integer'
        mymodule.db.SmallInteger = 'integer'
        mymodule.db.Float = 'number'
        mymodule.db.Boolean = 'boolean'
        mymodule.db.ForeignKey = db.ForeignKey
        sys.modules['mockedpackage'] = mymodule

    def parse(self, files):
        forget_keys = ['created_at', 'updated_at', 'deleted_at']
        db = SQLAlchemy()
        for file_path, file_name in files:
            spec = importlib.util.spec_from_file_location(
                file_name,
                file_path
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            models = (
                SuperDict(mod.__dict__)
                .kfilter(lambda k: k in self.parents
                )
            )
            for model in models:
                props = mod.__dict__[model].__dict__["_mock_return_value"]
                if not isinstance(mod.__dict__[model].__dict__["_mock_return_value"], dict):
                    continue
                table_name = props.get('__tablename__', model)
                self.data[table_name] = dict(
                    type='array',
                    items=dict(
                        properties=dict(),
                        required=[]
                    )
                )
                self.model_table[model] = table_name
                self.table_model[table_name] = model
                for key, val in props.items():
                    if key in forget_keys:
                        continue
                    if isinstance(val, db.Column):
                        type_col = val.name or val.type
                        if isinstance(type_col, TEXT):
                            type_col = 'string'
                        if isinstance(type_col, JSON):
                            type_col = 'object'
                        self.data[table_name]['items']['properties'][key] = dict(type=type_col)
                        if val.__dict__['foreign_keys']:
                            fk = list(val.__dict__['foreign_keys'])[0]
                            self.data[table_name]['items']['properties'][key]['foreign_key'] = fk.__dict__['_colspec']
                        if not val.__dict__['nullable']:
                            self.data[table_name]['items']['required'].append(key)

    def inherit(self):
        all_classes = set(self.parents.keys())
        not_treated = set(all_classes)
        treated = {'db.Model'}
        while not_treated:
            for model in not_treated:
                parent = self.parents[model]
                if parent not in treated:
                    continue
                treated.add(model)
                if parent == 'db.Model':
                    continue
                table_name = self.model_table[model]
                parent_props = self.data[self.model_table[parent]]['items']['properties']
                self.data[table_name]['items']['properties'] = dict(
                    **self.data[table_name]['items']['properties'],
                    **parent_props
                )
            not_treated -= treated

    def clear(self):
        if os.path.isdir(self.tmp_path):
            shutil.rmtree(self.tmp_path)

    def to_schema(self):
        return {
            "$schema": "http://json-schema.org/schema#",
            "type": "object",
            "properties": self.data,
        }
