import click

from cornflow.cli.arguments import verbose
from cornflow.cli.utils import get_app
from cornflow.commands.token_expiry import notify_api_key_expiry


@click.group(name="tokens", help="Commands to manage the long-lived tokens")
def tokens():
    """
    This method is empty but it serves as the building block
    for the rest of the commands
    """
    pass


@tokens.command(
    name="notify-expiry",
    help="Emails the owner and the platform administrators when a personal "
    "API key is close to expiring (thresholds in "
    "TOKEN_EXPIRY_NOTIFICATION_DAYS). Meant to be run once a day from cron or "
    "a Kubernetes CronJob: it is idempotent, so repeated runs send nothing "
    "extra, and it catches up after a missed run.",
)
@verbose
def notify_expiry(verbose):
    app = get_app()
    with app.app_context():
        notified = notify_api_key_expiry(verbose=verbose)
        click.echo(f"Sent expiry warnings for {notified} API key(s)")
        return True
