import json
import os

from .endpoint_tools import *
from .models_tools import *
from .schemas_tools import *
from .tools import *


class APIGenerator:
    def __init__(
        self,
        schema_path,
        app_name,
        output_path=None,
        options=None,
        name_table=None,
    ):
        self.path = schema_path
        self.name = app_name
        self.options = options
        if not self.options:
            self.options = ["all"]
        self.schema = self.import_schema()
        if self.schema["type"] == "array" and not name_table:
            self.schema = {"properties": {"data": self.schema}}
        elif self.schema["type"] == "array" and name_table:
            self.schema = {"properties": {name_table: self.schema}}
        elif self.schema["type"] != "array" and name_table:
            print(
                "The JSONSchema does not contain only one table. The --one option will be ignored"
            )
        self.output_path = output_path or "output"
        self.model_path = os.path.join(self.output_path, "models")
        self.endpoint_path = os.path.join(self.output_path, "endpoints")
        self.schema_path = os.path.join(self.output_path, "schemas")

    def import_schema(self):
        with open(self.path, "r") as fd:
            schema = json.load(fd)
        return schema

    def prepare_dirs(self):
        if not os.path.isdir(self.output_path):
            os.mkdir(self.output_path)
        if not os.path.isdir(self.model_path):
            os.mkdir(self.model_path)
        init_path = os.path.join(self.model_path, "__init__.py")
        open(init_path, "w").close()
        if not os.path.isdir(self.endpoint_path):
            os.mkdir(self.endpoint_path)
        init_path = os.path.join(self.endpoint_path, "__init__.py")
        open(init_path, "w").close()
        if not os.path.isdir(self.schema_path):
            os.mkdir(self.schema_path)
        init_path = os.path.join(self.schema_path, "__init__.py")
        open(init_path, "w").close()

    def main(self):
        self.prepare_dirs()
        print("DIRECTORIES CREATED SUCCESSFULLY")
        tables = self.schema["properties"].keys()
        for table in tables:
            if self.schema["properties"][table]["type"] != "array":
                print(
                    f'\nThe table "{table}" does not have the correct format. '
                    f"The structures will not be generated for this table"
                )
                continue
            model_name = self.new_model(table)
            schemas_names = self.new_schemas(table)
            self.new_endpoint(table, model_name, schemas_names)
        print(
            f"The generated files will be stored in {os.path.join(os.getcwd(), self.output_path)}\n"
        )

    def new_model(self, table_name):
        filename = os.path.join(self.model_path, self.name + "_" + table_name + ".py")
        class_name = self.snake_to_camel(self.name + "_" + table_name + "_model")
        parents_class = ["TraceAttributesModel"]
        mg = ModelGenerator(
            class_name, self.schema, parents_class, table_name, self.name
        )
        with open(filename, "w") as fd:
            fd.write(model_shared_imports)
            fd.write("\n")
            fd.write(generate_class_def(class_name, parents_class))
            fd.write(mg.generate_model_description())
            fd.write("\n")
            fd.write(mg.generate_table_name())
            fd.write("\n")
            fd.write(mg.generate_model_fields())
            fd.write("\n")
            fd.write(mg.generate_model_init())
            fd.write("\n")
            fd.write(mg.generate_model_repr_str())
            fd.write("\n")
        return class_name

    def new_endpoint(self, table_name, model_name, schemas_names):
        filename = os.path.join(
            self.endpoint_path, self.name + "_" + table_name + ".py"
        )
        class_name_all = self.snake_to_camel(self.name + "_" + table_name + "_endpoint")
        class_name_details = self.snake_to_camel(
            self.name + "_" + table_name + "_details_endpoint"
        )
        parents_class = ["BaseMetaResource"]
        roles_with_access = ["SERVICE_ROLE"]
        eg = EndpointGenerator(table_name, self.name, model_name, schemas_names)
        with open(filename, "w") as fd:
            # Global
            fd.write(eg.generate_endpoints_imports())
            fd.write("\n")
            fd.write(generate_class_def(class_name_all, parents_class))
            fd.write(eg.generate_endpoint_description())
            fd.write("\n")
            fd.write(f'    ROLES_WITH_ACCESS = [{", ".join(roles_with_access)}]\n')
            fd.write("\n")
            fd.write(eg.generate_endpoint_init())
            fd.write("\n")
            if "getAll" in self.options or "all" in self.options:
                fd.write(eg.generate_endpoint_get_all())
                fd.write("\n")
            fd.write(eg.generate_endpoint_post())
            fd.write("\n")
            if "deleteAll" in self.options or "all" in self.options:
                fd.write(eg.generate_endpoint_delete_all())

            fd.write("\n\n")
            if any(m in self.options for m in ["getOne", "update", "deleteOne", "all"]):
                # Details
                fd.write(generate_class_def(class_name_details, parents_class))
                fd.write(eg.generate_endpoint_description())
                fd.write("\n")
                fd.write(f'    ROLES_WITH_ACCESS = [{", ".join(roles_with_access)}]\n')
                fd.write("\n")
                fd.write(eg.generate_endpoint_init())
                fd.write("\n")
                if "getOne" in self.options or "all" in self.options:
                    fd.write(eg.generate_endpoint_get_one())
                    fd.write("\n")
                if "update" in self.options or "all" in self.options:
                    fd.write(eg.generate_endpoint_put())
                    fd.write("\n")
                if "deleteOne" in self.options or "all" in self.options:
                    fd.write(eg.generate_endpoint_delete_one())
                    fd.write("\n")

    def new_schemas(self, table_name):
        filename = os.path.join(self.schema_path, self.name + "_" + table_name + ".py")
        class_name_one = self.snake_to_camel(self.name + "_" + table_name + "_response")
        class_name_edit = self.snake_to_camel(
            self.name + "_" + table_name + "_edit_request"
        )
        class_name_post = self.snake_to_camel(
            self.name + "_" + table_name + "_post_request"
        )
        parents_class = ["Schema"]
        partial_schema = self.schema["properties"][table_name]["items"]
        sg = SchemaGenerator(partial_schema, table_name, self.name)
        with open(filename, "w") as fd:
            fd.write(sg.generate_schema_file_description())
            fd.write(schemas_imports)
            fd.write("\n")
            fd.write(generate_class_def(class_name_edit, parents_class))
            fd.write(sg.generate_edit_schema())
            fd.write("\n\n")

            fd.write(generate_class_def(class_name_post, parents_class))
            fd.write(sg.generate_post_schema())
            fd.write("\n\n")

            parents_class = [class_name_post]
            fd.write(generate_class_def(class_name_one, parents_class))
            fd.write(sg.generate_schema())
        return {
            "one": class_name_one,
            "editRequest": class_name_edit,
            "postRequest": class_name_post,
        }

    @staticmethod
    def snake_to_camel(name):
        return "".join(word.title() for word in name.split("_"))
