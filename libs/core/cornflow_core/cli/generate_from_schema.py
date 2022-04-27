import click

from .api_generator import APIGenerator

# TODO: change choices of remove_method to: get-list, get-detail, post-list, put-detail, patch-detail, delete-detail
METHOD_OPTIONS = ["getOne", "getAll", "update", "deleteOne", "deleteAll"]


@click.command(name="generate_from_schema")
@click.option("--path", "-p", type=str, help="The absolute path to the JSONSchema")
@click.option(
    "--app-name", "-a", type=str, default="", help="The name of the application"
)
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
    "--one",
    type=str,
    help="If your schema describes only one table, use this option to indicate the name of the table",
    required=False,
)
def generate_from_schema(path, app_name, output_path, remove_methods, one):
    """

    :param path:
    :type path:
    :param app_name:
    :type app_name:
    :param output_path:
    :type output_path:
    :param remove_methods:
    :type remove_methods:
    :param one:
    :type one:
    :return:
    :rtype:
    """
    path = path.replace("\\", "/")
    output = None
    if output_path != "output":
        output = output_path.replace("\\", "/")

    if remove_methods is not None:
        methods_to_add = list(set(METHOD_OPTIONS) - set(remove_methods))
    else:
        methods_to_add = []

    name_table = None
    if one:
        name_table = one

    click.echo("Generating REST API components from the provided JSONSchema")
    click.echo(f"The path to the JSONSchema is {path}")
    click.echo(f"The app_name is {app_name}")
    click.echo(f"The output_path is {output}")
    click.echo(f"The methods to add is {methods_to_add}")
    click.echo(f"The name_table is {name_table}")

    APIGenerator(
        path,
        app_name=app_name,
        output_path=output_path,
        options=methods_to_add,
        name_table=name_table,
    ).main()
