import click

from cornflow_core.cli.tools.schema_generator import SchemaGenerator


@click.command(name="schema_from_models")
@click.option(
    "--path",
    "-p",
    type=str,
    help="The absolute path to folder containing the models",
    required=True,
)
@click.option("--output-path", "-o", type=str, help="The output path", required=False)
@click.option(
    "--ignore-files",
    "-i",
    type=str,
    help="Files that will be ignored (with the .py extension). "
    "__init__.py files are automatically ignored. Ex: 'instance.py'",
    multiple=True,
    required=False,
)
@click.option(
    "--leave-bases/--no-leave-bases",
    "-l/-nl",
    default=False,
    help="Use this option to leave the bases classes BaseDataModel, "
    "EmptyModel and TraceAttributes in the schema. By default, they will be deleted",
)
def schema_from_models(path, output_path, ignore_files, leave_bases):
    """

    :param str path: the path to the folder that contains the models
    :param output_path: the output path where the JSONSchema should be placed
    :param str ignore_files: files to be ignored.
    :param str leave_bases: if the JSONSchema should have abstract classes used as the base for other clases.
    :return: a click status code
    :rtype: int
    """
    path = path.replace("\\", "/")
    output = None
    if output_path:
        output = output_path.replace("\\", "/")

    if ignore_files:
        ignore_files = list(ignore_files)

    click.echo("Generating JSONSchema file from the REST API")
    click.echo(f"The path to the JSONSchema is {path}")
    click.echo(f"The output_path is {output}")
    click.echo(f"The ignore_files is {ignore_files}")
    click.echo(f"The leave_bases is {leave_bases}")

    SchemaGenerator(
        path, output_path=output, ignore_files=ignore_files, leave_bases=leave_bases
    ).main()
