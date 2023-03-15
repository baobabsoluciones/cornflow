import click

verbose = click.option("-v", "--verbose", is_flag=True, default=False)
app_name = click.option(
    "-a",
    "--app_name",
    required=False,
    type=str,
    default="external_app",
    help="The name of the external app",
)

username = click.option(
    "-u", "--username", required=True, type=str, help="The username of the user"
)
password = click.option(
    "-p", "--password", required=True, type=str, help="The password of the user"
)
email = click.option(
    "-e", "--email", required=True, type=str, help="The email of the user"
)
path = click.option(
    "-p", "--path", type=str, help="The path to the file to save the file"
)
