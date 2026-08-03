import click

from cornflow.cli.utils import get_app
from cornflow.models import SessionModel
from cornflow.shared import db


@click.group(name="sessions", help="Commands to manage the refresh-token sessions")
def sessions():
    """
    This method is empty but it serves as the building block
    for the rest of the commands
    """
    pass


@sessions.command(
    name="purge",
    help="Deletes the revoked or expired refresh-token session rows. Active "
    "sessions are purged opportunistically at login; run this periodically "
    "(e.g. from a cron job) to also clean up the sessions of inactive users.",
)
def purge_sessions():
    app = get_app()
    with app.app_context():
        deleted = SessionModel.purge_stale()
        db.session.commit()
        click.echo(f"Deleted {deleted} stale sessions")
        return True
