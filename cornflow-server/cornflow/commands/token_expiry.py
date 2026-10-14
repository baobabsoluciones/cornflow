"""
Expiry notifications for the personal API keys.

The keys themselves are never stored (they are shown once), only the instant
they were issued, so the expiry is ``api_key_issued_at +
API_KEY_DURATION_DAYS``. This command is meant to be run **once a day** by an
external scheduler (cron, a Kubernetes CronJob...): cornflow has no scheduler
of its own.

For every user with an active key it works out the days left and sends the
warning for the largest configured threshold not yet notified, to the owner
and to every platform administrator. Recording the threshold makes the command
idempotent (running it twice a day sends nothing extra) and resilient to
missed runs: if the job does not run for a week, the next run sends one
warning with the real days left instead of staying silent.
"""

from flask import current_app

from cornflow.models import UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.audit import audit
from cornflow.shared.const import PLATFORM_ADMIN_ROLE
from cornflow.shared.email import get_api_key_expiry_email, send_email_to


def get_notification_thresholds():
    """
    The configured thresholds (in days), largest first.

    :return: the list of thresholds
    :rtype: list
    """
    raw = current_app.config.get("TOKEN_EXPIRY_NOTIFICATION_DAYS", "30,7,3,2,1")
    thresholds = []
    for chunk in str(raw).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            thresholds.append(int(chunk))
        except ValueError:
            current_app.logger.warning(
                f"Ignoring invalid API key expiry threshold: {chunk!r}"
            )
    return sorted(set(thresholds), reverse=True)


def get_threshold_to_notify(days_left, already_notified, thresholds):
    """
    The threshold to record when notifying now, or None when there is nothing
    to send.

    The rule is "days_left <= threshold" (not equality), so a missed run is
    caught up on the next one instead of staying silent. Of the thresholds
    already crossed the *smallest* is recorded: the email always states the
    real days left, so every crossed threshold is covered by that single
    notice and running the command twice in one day sends nothing extra.

    :param int days_left: whole days left before the key expires
    :param already_notified: smallest threshold already notified (or None)
    :param list thresholds: the configured thresholds
    :return: the threshold to record, or None when there is nothing to send
    """
    crossed = [threshold for threshold in thresholds if days_left <= threshold]
    if not crossed:
        return None
    smallest = min(crossed)
    if already_notified is not None and smallest >= already_notified:
        return None
    return smallest


def get_platform_admin_emails():
    """
    Email addresses of the platform administrators, who are warned about every
    expiring key (the owner of a service account key may well be a mailbox
    nobody reads).

    :return: the list of email addresses
    :rtype: list
    """
    rows = UserRoleModel.query.filter_by(role_id=PLATFORM_ADMIN_ROLE).all()
    emails = []
    for row in rows:
        user = UserModel.get_one_user(row.user_id)
        if user is not None and user.email:
            emails.append(user.email)
    return sorted(set(emails))


def _email_config():
    """
    The SMTP settings, or None when email is not configured on the deployment.
    """
    config = current_app.config
    settings = (
        config.get("SERVICE_EMAIL_ADDRESS"),
        config.get("SERVICE_EMAIL_PASSWORD"),
        config.get("SERVICE_EMAIL_SERVER"),
        config.get("SERVICE_EMAIL_PORT"),
    )
    if any(value is None for value in settings):
        return None
    return settings


def notify_api_key_expiry(verbose: bool = False) -> int:
    """
    Sends the pending expiry warnings for the active personal API keys.

    :param bool verbose: log a line per notified key
    :return: the number of keys a warning was sent for
    :rtype: int
    """
    if int(current_app.config.get("TOKEN_EXPIRY_NOTIFICATIONS_ENABLED", 1)) != 1:
        current_app.logger.info("API key expiry notifications are disabled")
        return 0

    thresholds = get_notification_thresholds()
    if not thresholds:
        current_app.logger.warning(
            "No valid API key expiry thresholds configured, nothing to do"
        )
        return 0

    email_settings = _email_config()
    admin_emails = get_platform_admin_emails()
    notified = 0

    users = UserModel.query.filter(UserModel.api_key_issued_at.isnot(None)).all()
    for user in users:
        days_left = user.api_key_days_left()
        if days_left is None:
            continue
        threshold = get_threshold_to_notify(
            days_left, user.api_key_expiry_notified, thresholds
        )
        if threshold is None:
            continue

        expires_at = user.api_key_expires_at()
        recipients = [(user.email, True)] + [
            (email, False) for email in admin_emails if email != user.email
        ]
        for receiver, is_owner in recipients:
            if not receiver or email_settings is None:
                continue
            sender, password, smtp_server, port = email_settings
            try:
                send_email_to(
                    email=get_api_key_expiry_email(
                        username=user.username,
                        days_left=days_left,
                        expires_at=expires_at.strftime("%Y-%m-%d"),
                        service_name=current_app.config["SERVICE_NAME"],
                        sender=sender,
                        receiver=receiver,
                        is_owner=is_owner,
                    ),
                    smtp_server=smtp_server,
                    port=port,
                    sender=sender,
                    password=password,
                    receiver=receiver,
                )
            except Exception as error:
                # A failing recipient must not stop the rest of the run
                current_app.logger.error(
                    f"Could not send the API key expiry warning of user "
                    f"{user.id} to {receiver}: {error}"
                )

        if email_settings is None:
            current_app.logger.warning(
                f"Email is not configured: the API key of user {user.id} "
                f"expires in {days_left} day(s) and no warning could be sent"
            )

        # The threshold is recorded even when the email could not be sent, so
        # a broken mail server does not turn the run into a repeated retry;
        # the audit event is always emitted.
        user.api_key_expiry_notified = threshold
        db.session.add(user)
        audit(
            "apikey.expiry_notified",
            actor="scheduler",
            target_id=user.id,
            target=user.username,
            days_left=days_left,
            threshold=threshold,
            recipients=len(recipients),
            email_sent=email_settings is not None,
        )
        notified += 1
        if verbose:
            current_app.logger.info(
                f"API key of user {user.username} expires in {days_left} "
                f"day(s): warning sent (threshold {threshold})"
            )

    db.session.commit()
    return notified
