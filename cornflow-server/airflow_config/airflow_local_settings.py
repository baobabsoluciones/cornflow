# AIRFLOW custom settings for CornflowEnv
# Airflow 3 moved UIAlert to airflow.api_fastapi and dropped STATE_COLORS (the new UI
# manages its own theme), so only the dashboard alert is kept.

from airflow.api_fastapi.common.types import UIAlert

DASHBOARD_UIALERTS = [
    UIAlert(
        text="Welcome! This is the backend of your cornflow environment. Airflow is a platform created by the community to programmatically author, schedule and monitor workflows.",
        category="info",
    ),
]
