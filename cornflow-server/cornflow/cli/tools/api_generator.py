"""
This file has the class that creates the new API
"""
import json
import os

from .endpoint_tools import EndpointGenerator
from .models_tools import ModelGenerator, model_shared_imports
from .schemas_tools import SchemaGenerator, schemas_imports
from .tools import generate_class_def


class APIGenerator:
    """
    This class is used to create the new API
    """

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

    def import_schema(self) -> dict:
        """
        This method imports the JSONSchema file

        :return: the read schema
        :rtype: dict
        """
        with open(self.path, "r") as fd:
            schema = json.load(fd)
        return schema

    def prepare_dirs(self):
        """
        This method creates all the folders needed

        :return: None
        :rtype: None
        """
        if not os.path.isdir(self.output_path):
            os.mkdir(self.output_path)
        if not os.path.isdir(self.model_path):
            os.mkdir(self.model_path)

        init_path = os.path.join(self.model_path, "__init__.py")
        with open(init_path, "w") as file:
            file.write(f'"""\nThis file exposes the models\n"""\n')

        if not os.path.isdir(self.endpoint_path):
            os.mkdir(self.endpoint_path)

        init_path = os.path.join(self.endpoint_path, "__init__.py")
        with open(init_path, "w") as file:
            file.write(f'"""\nThis file exposes the endpoints\n"""\n')

        if not os.path.isdir(self.schema_path):
            os.mkdir(self.schema_path)

        init_path = os.path.join(self.schema_path, "__init__.py")
        with open(init_path, "w") as file:
            file.write(f'"""\nThis file exposes the schemas\n"""\n')

    def main(self):
        """
        This is the main method that gets executed

        :return: None
        :rtype: None
        """
        self.prepare_dirs()
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

        init_file = os.path.join(self.endpoint_path, "__init__.py")
        with open(init_file, "a") as file:
            file.write("\nresources = []\n")
        print(
            f"The generated files will be stored in {os.path.join(os.getcwd(), self.output_path)}\n"
        )
        return 0

    def new_model(self, table_name):
        """
        This method takes a table name and creates a flask database model with the fields os said table

        :param str table_name: the name of the table to create
        :return: the name of the created model
        :rtype: str
        """
        if self.name is None:
            filename = os.path.join(self.model_path, f"{table_name}.py")
            class_name = self.snake_to_camel(table_name + "_model")
        else:
            filename = os.path.join(self.model_path, f"{self.name}_{table_name}.py")
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

        init_file = os.path.join(self.model_path, "__init__.py")

        with open(init_file, "a") as file:
            if self.name is None:
                file.write(f"from .{table_name} import {class_name}\n")
            else:
                file.write(f"from .{self.name}_{table_name} import {class_name}\n")

        return class_name

    def new_schemas(self, table_name: str) -> dict:
        """
        This method takes a table name and creates a flask database model with the fields os said table

        :param str table_name: the name of the table to create
        :return: the dictionary with the names of the schemas created
        :rtype: dict
        """
        if self.name is None:
            filename = os.path.join(self.schema_path, table_name + ".py")
            class_name_one = self.snake_to_camel(table_name + "_response")
            class_name_edit = self.snake_to_camel(table_name + "_edit_request")
            class_name_post = self.snake_to_camel(table_name + "_post_request")
            class_name_post_bulk = self.snake_to_camel(table_name + "_post_bulk_request")
            class_name_put_bulk = self.snake_to_camel(table_name + "_put_bulk_request")
            class_name_put_bulk_one = class_name_put_bulk + "One"
        else:
            filename = os.path.join(
                self.schema_path, self.name + "_" + table_name + ".py"
            )
            class_name_one = self.snake_to_camel(
                self.name + "_" + table_name + "_response"
            )
            class_name_edit = self.snake_to_camel(
                self.name + "_" + table_name + "_edit_request"
            )
            class_name_post = self.snake_to_camel(
                self.name + "_" + table_name + "_post_request"
            )
            class_name_post_bulk = self.snake_to_camel(
                self.name + "_" + table_name + "_post_bulk_request"
            )
            class_name_put_bulk = self.snake_to_camel(
                self.name + "_" + table_name + "_put_bulk_request"
            )
            class_name_put_bulk_one = class_name_put_bulk + "One"

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

            fd.write(generate_class_def(class_name_post_bulk, parents_class))
            fd.write(sg.generate_bulk_schema(class_name_post))
            fd.write("\n\n")

            parents_class = [class_name_edit]
            fd.write(generate_class_def(class_name_put_bulk_one, parents_class))
            fd.write(sg.generate_put_bulk_schema_one())
            fd.write("\n\n")

            parents_class = ["Schema"]
            fd.write(generate_class_def(class_name_put_bulk, parents_class))
            fd.write(sg.generate_bulk_schema(class_name_put_bulk_one))
            fd.write("\n\n")

            parents_class = [class_name_post]
            fd.write(generate_class_def(class_name_one, parents_class))
            fd.write(sg.generate_schema())

        init_file = os.path.join(self.schema_path, "__init__.py")
        with open(init_file, "a") as file:
            if self.name is None:
                file.write(
                    f"from .{table_name} import {class_name_one}, "
                    f"{class_name_edit}, {class_name_post}, {class_name_post_bulk}, {class_name_put_bulk}\n"
                )
            else:
                file.write(
                    f"from .{self.name}_{table_name} import {class_name_one}, "
                    f"{class_name_edit}, {class_name_post}, {class_name_post_bulk}, {class_name_put_bulk}\n"
                )

        return {
            "one": class_name_one,
            "editRequest": class_name_edit,
            "postRequest": class_name_post,
            "postBulkRequest": class_name_post_bulk,
            "putBulkRequest": class_name_put_bulk
        }

    def new_endpoint(
        self, table_name: str, model_name: str, schemas_names: dict
    ) -> None:
        """
        This method takes a table name, a model_name and the names of the marshmallow schemas and
        creates a flask endpoint with the methods passed

        :param str table_name: the name of the table to create
        :param str model_name: the name of the model that have been created
        :param dict schemas_names: the names of the schemas that have been created
        :return: None
        :rtype: None
        """
        if self.name is None:
            filename = os.path.join(self.endpoint_path, table_name + ".py")
            class_name_all = self.snake_to_camel(table_name + "_endpoint")
            class_name_details = self.snake_to_camel(table_name + "_details_endpoint")
            class_name_bulk = self.snake_to_camel(table_name + "_bulk_endpoint")
        else:
            filename = os.path.join(
                self.endpoint_path, self.name + "_" + table_name + ".py"
            )
            class_name_all = self.snake_to_camel(
                self.name + "_" + table_name + "_endpoint"
            )
            class_name_details = self.snake_to_camel(
                self.name + "_" + table_name + "_details_endpoint"
            )
            class_name_bulk = self.snake_to_camel(
                self.name + "_" + table_name + "_bulk_endpoint"
            )

        parents_class = ["BaseMetaResource"]
        roles_with_access = ["SERVICE_ROLE"]
        eg = EndpointGenerator(table_name, self.name, model_name, schemas_names)
        with open(filename, "w") as fd:
            # Global
            if any(m in self.options for m in ["get_list", "post_list", "all"]):
                fd.write(eg.generate_endpoints_imports())
                fd.write("\n")
                fd.write(generate_class_def(class_name_all, parents_class))
                fd.write(eg.generate_endpoint_description())
                fd.write("\n")
                fd.write(f'    ROLES_WITH_ACCESS = [{", ".join(roles_with_access)}]\n')
                fd.write("\n")
                fd.write(eg.generate_endpoint_init())
                fd.write("\n")
                if "get_list" in self.options or "all" in self.options:
                    fd.write(eg.generate_endpoint_get_all())
                    fd.write("\n")
                if "post_list" in self.options or "all" in self.options:
                    fd.write(eg.generate_endpoint_post())
                    fd.write("\n")

            fd.write("\n")

            if any(
                m in self.options
                for m in [
                    "get_detail",
                    "put_detail",
                    "patch_detail",
                    "delete_detail",
                    "all",
                ]
            ):
                # Details
                fd.write(generate_class_def(class_name_details, parents_class))
                fd.write(eg.generate_endpoint_description())
                fd.write("\n")
                fd.write(f'    ROLES_WITH_ACCESS = [{", ".join(roles_with_access)}]\n')
                fd.write("\n")
                fd.write(eg.generate_endpoint_init())
                fd.write("\n")
                if "get_detail" in self.options or "all" in self.options:
                    fd.write(eg.generate_endpoint_get_one())
                    fd.write("\n")
                if "put_detail" in self.options or "all" in self.options:
                    fd.write(eg.generate_endpoint_put())
                    fd.write("\n")
                if "patch_detail" in self.options or "all" in self.options:
                    fd.write(eg.generate_endpoint_patch())
                    fd.write("\n")
                if "delete_detail" in self.options or "all" in self.options:
                    fd.write(eg.generate_endpoint_delete_one())
                    fd.write("\n")

            fd.write("\n")

            if any(
                m in self.options
                for m in [
                    "post_bulk",
                    "put_bulk"
                ]
            ):
                # Bulk post/put
                fd.write(generate_class_def(class_name_bulk, parents_class))
                fd.write(eg.generate_endpoint_description())
                fd.write("\n")
                fd.write(f'    ROLES_WITH_ACCESS = [{", ".join(roles_with_access)}]\n')
                fd.write("\n")
                fd.write(eg.generate_endpoint_init())
                fd.write("\n")
                if "post_bulk" in self.options or "all" in self.options:
                    fd.write(eg.generate_endpoint_post_bulk())
                    fd.write("\n")
                if "put_bulk" in self.options or "all" in self.options:
                    fd.write(eg.generate_endpoint_put_bulk())
                    fd.write("\n")

        init_file = os.path.join(self.endpoint_path, "__init__.py")
        with open(init_file, "a") as file:
            if any(m in self.options for m in ["get_list", "post_list", "all"]):
                if any(
                    m in self.options
                    for m in [
                        "get_detail",
                        "put_detail",
                        "patch_detail",
                        "delete_detail",
                        "all",
                    ]
                ):
                    if self.name is None:
                        file.write(
                            f"from .{table_name} import {class_name_all}, {class_name_details}\n"
                        )
                    else:
                        file.write(
                            f"from .{self.name}_{table_name} import {class_name_all}, {class_name_details}\n"
                        )
                else:
                    if self.name is None:
                        file.write(f"from .{table_name} import {class_name_all}\n")
                    else:
                        file.write(
                            f"from .{self.name}_{table_name} import {class_name_all}\n"
                        )
            elif any(
                m in self.options
                for m in [
                    "get_detail",
                    "put_detail",
                    "patch_detail",
                    "delete_detail",
                    "all",
                ]
            ):
                if self.name is None:
                    file.write(f"from .{table_name} import {class_name_details}\n")
                else:
                    file.write(
                        f"from .{self.name}_{table_name} import {class_name_details}\n"
                    )

            elif any(
                m in self.options
                for m in ["post_bulk", "put_bulk"]
            ):
                if self.name is None:
                    file.write(f"from .{table_name} import {class_name_bulk}\n")
                else:
                    file.write(
                        f"from .{self.name}_{table_name} import {class_name_bulk}\n"
                    )

    @staticmethod
    def snake_to_camel(name: str) -> str:
        """
        This static method takes a name with underscores in it and changes it to camelCase

        :param str name: the name to mutate
        :return: the mutated name
        :rtype: str
        """
        return "".join(word.title() for word in name.split("_"))
