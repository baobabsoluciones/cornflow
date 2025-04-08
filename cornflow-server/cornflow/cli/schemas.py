"""
File that implements the generate from schema cli command
"""

import click
from .tools.api_generator import APIGenerator
from .tools.schema_generator import SchemaGenerator
import json

METHOD_OPTIONS = [
    "get_list",
    "post_list",
    "get_detail",
    "put_detail",
    "patch_detail",
    "delete_detail",
    "post_bulk",
    "put_bulk",
]


@click.group(name="schemas", help="Commands to manage the schemas")
def schemas():
    """
    This method is empty but it serves as the building block
    for the rest of the commands
    """
    pass


@schemas.command(
    name="generate_from_schema",
    help="Command to generate models, endpoints and schemas from a jsonschema",
)
@click.option(
    "--path", "-p", type=str, help="The absolute path to the JSONSchema", required=True
)
@click.option("--app-name", "-a", type=str, help="The name of the application")
@click.option(
    "--output-path",
    "-o",
    type=str,
    default="output",
    help="The output path",
    required=False,
)
@click.option(
    "--remove-methods",
    "-r",
    type=click.Choice(METHOD_OPTIONS, case_sensitive=False),
    help="Methods that will NOT be added to the new endpoints",
    multiple=True,
    required=False,
)
@click.option(
    "--one",
    type=str,
    help="If your schema describes only one table, use this option to indicate the name of the table",
    required=False,
)
@click.option(
    "--endpoints-methods",
    "-m",
    type=str,
    default=None,
    help="json file with dict of methods that will be added to each new endpoints",
    required=False,
)
@click.option(
    "--endpoints-access",
    "-e",
    type=str,
    default=None,
    help="json file with dict of roles access that will be added to each new endpoints",
    required=False,
)
def generate_from_schema(
    path,
    app_name,
    output_path,
    remove_methods,
    one,
    endpoints_methods,
    endpoints_access,
):
    """
    This method is executed for the command and creates all the files for the REST API from the provided JSONSchema

    :param str path: the path to the JSONSchema file.
    :param str app_name: the name of the application.
    :param str output_path: the output path.
    :param tuple remove_methods: the methods that will not be added to the new endpoints.
    :param str one: if your schema describes only one table, use this option to indicate the name of the table.
    :param str endpoints_methods: json file with dict of methods that will be added to each new endpoints.
    :param str endpoints_access: json file with dict of roles access that will be added to each new endpoints.
    :return: a click status code
    :rtype: int
    """

    path = path.replace("\\", "/")
    output = None
    if output_path != "output":
        output = output_path.replace("\\", "/")

    if remove_methods is not None:
        methods_to_add = {"default": list(set(METHOD_OPTIONS) - set(remove_methods))}
    else:
        methods_to_add = {"default": list(set(METHOD_OPTIONS))}

    if endpoints_methods is not None:
        endpoints_methods = endpoints_methods.replace("\\", "/")
        with open(endpoints_methods, "r") as file:
            methods_to_add.update(json.load(file))

    dict_endpoints_access = {"default": ["SERVICE_ROLE"]}
    if endpoints_access is not None:
        endpoints_access = endpoints_access.replace("\\", "/")
        with open(endpoints_access, "r") as file:
            dict_endpoints_access.update(json.load(file))

    name_table = None
    if one:
        name_table = one

    click.echo("Generating REST API components from the provided JSONSchema")
    click.echo(f"The path to the JSONSchema is {path}")
    click.echo(f"The app_name is {app_name}")
    click.echo(f"The output_path is {output}")
    click.echo(f"The method to add are obtained from {endpoints_methods}")
    click.echo(f"The methods to add are {methods_to_add}")
    click.echo(f"The roles to add are {endpoints_access}")
    click.echo(f"The name_table is {name_table}")

    APIGenerator(
        path,
        app_name=app_name,
        output_path=output_path,
        options=methods_to_add,
        name_table=name_table,
        endpoints_access=dict_endpoints_access,
    ).main()


# @schemas.command(
#     name="schema_from_models",
#     help="Command to generate a jsonschema from a set of models",
# )
# @click.option(
#     "--path",
#     "-p",
#     type=str,
#     help="The absolute path to folder containing the models",
#     required=True,
# )
# @click.option("--output-path", "-o", type=str, help="The output path", required=False)
# @click.option(
#     "--ignore-files",
#     "-i",
#     type=str,
#     help="Files that will be ignored (with the .py extension). "
#     "__init__.py files are automatically ignored. Ex: 'instance.py'",
#     multiple=True,
#     required=False,
# )
# @click.option(
#     "--leave-bases/--no-leave-bases",
#     "-l/-nl",
#     default=False,
#     help="Use this option to leave the bases classes BaseDataModel, "
#     "EmptyModel and TraceAttributes in the schema. By default, they will be deleted",
# )
# def schema_from_models(path, output_path, ignore_files, leave_bases):
#     """
#
#     :param str path: the path to the folder that contains the models
#     :param output_path: the output path where the JSONSchema should be placed
#     :param str ignore_files: files to be ignored.
#     :param str leave_bases: if the JSONSchema should have abstract classes used as the base for other clases.
#     :return: a click status code
#     :rtype: int
#     """
#     path = path.replace("\\", "/")
#     output = None
#     if output_path:
#         output = output_path.replace("\\", "/")
#
#     if ignore_files:
#         ignore_files = list(ignore_files)
#
#     click.echo("Generating JSONSchema file from the REST API")
#     click.echo(f"The path to the JSONSchema is {path}")
#     click.echo(f"The output_path is {output}")
#     click.echo(f"The ignore_files is {ignore_files}")
#     click.echo(f"The leave_bases is {leave_bases}")
#
#     SchemaGenerator(
#         path, output_path=output, ignore_files=ignore_files, leave_bases=leave_bases
#     ).main()
#
#     return True
