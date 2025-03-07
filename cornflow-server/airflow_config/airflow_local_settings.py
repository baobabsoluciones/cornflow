# AIRFLOW custom UI colors for CornflowEnv

STATE_COLORS = {
    "deferred": "#7c4fe0",
    "failed": "#c9301c",
    "queued": "#656d78",
    "removed": "#7bdcb5",
    "restarting": "#9b51e0",
    "running": "#01FF70",
    "scheduled": "#fcb900",
    "shutdown": "blue",
    "skipped": "darkorchid",
    "success": "#00d084",
    "up_for_reschedule": "#f78da7",
    "up_for_retry": "yellow",
    "upstream_failed": "#b31e1e",
}

from airflow.www.utils import UIAlert

DASHBOARD_UIALERTS = [
    UIAlert("Welcome! This is the backend of your cornflow environment. Airflow™ is a platform created by the community to programmatically author, schedule and monitor workflows."),
]