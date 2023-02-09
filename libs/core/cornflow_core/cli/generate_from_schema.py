"""
File that implements the generate from schema cli command
"""
import click
import json
from cornflow_core.cli.tools.api_generator import APIGenerator

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


@click.command(name="generate_from_schema")
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
    "--remove_methods",
    "-r",
    type=click.Choice(METHOD_OPTIONS, case_sensitive=False),
    help="Methods that will NOT be added to the new endpoints",
    multiple=True,
    required=False,
)
@click.option(
    "--endpoints_methods",
    "-m",
    type=str,
    default=None,
    help="json file with dict of methods that will be added to each new endpoints",
    required=False,
)
@click.option(
    "--endpoints_access",
    "-a",
    type=str,
    default=None,
    help="json file with dict of roles access that will be added to each new endpoints",
    required=False,
)
@click.option(
    "--one",
    type=str,
    help="If your schema describes only one table, use this option to indicate the name of the table",
    required=False,
)
def generate_from_schema(
    path, app_name, output_path, remove_methods, one, endpoints_methods, endpoints_access
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
            methods_to_add = json.load(file)

    if endpoints_access is not None:
        endpoints_access = endpoints_access.replace("\\", "/")
        with open(endpoints_access, "r") as file:
            endpoints_access = json.load(file)
    else:
        endpoints_access = {"default":["SERVICE_ROLE"]}

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
        endpoints_access=endpoints_access
    ).main()
