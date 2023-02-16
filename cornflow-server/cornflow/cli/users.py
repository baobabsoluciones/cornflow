import click


@click.group(name="users", help="Commands to manage the users")
def users():
    pass


@users.command(name="create", help="Create a user")
@click.option("--username", "-u", type=str, help="The username of the user")
@click.option("--password", "-p", type=str, help="The password of the user")
@click.option("--email", "-e", type=str, help="The email of the user")
@click.option("--role", "-r", type=str, help="The role of the user")
def create_user(username, password, email, role):
    pass
