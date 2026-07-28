"""
Benchmark comparing two implementations of the same GET endpoint
(execution + instance ``data``, plus ``config``) when those JSON fields
are very large:

- DAGDetailEndpoint: two full ORM object fetches. DEPRECATED, no longer
  routed in the live app -- registered here on a benchmark-only path.
- DAGDetailEndpointRaw: one column-pruned JOIN query that casts the JSON
  columns to text, skipping decode entirely, and splices the raw JSON text
  straight into a hand-built response body. This is the live implementation,
  routed at ``/dag/<idx>/``.

This is a standalone script, not a pytest test (the filename does not match
``test_*.py`` so it is never collected). It uses the Flask test client, so
timings reflect server-side (ORM + JSON (de)serialization) overhead rather
than network latency.

Run from ``cornflow-server``:

    python -m cornflow.tests.load.benchmark_dag_endpoint
"""

import json
import statistics
import time

from cornflow.endpoints.dag import DAGDetailEndpoint
from cornflow.models import ExecutionModel, InstanceModel
from cornflow.shared import db
from cornflow.tests.base_test_execution import TestExecutionsDetailEndpointMock
from cornflow.tests.const import DAG_URL
from cornflow.tests.load._deprecated_routes import (
    grant_get_permission,
    register_deprecated_route,
)

# Target size (bytes) of EACH of the instance.data / execution.data JSON blobs.
TARGET_BYTES = 100 * 1024 * 1024

# Number of timed GET requests per endpoint. Each request round-trips the
# full ~TARGET_BYTES JSON payload through Flask's JSON encoder, so keep this
# modest unless you're prepared to wait a while.
NUM_REQUESTS = 20

VARIANTS = [
    ("original", "_benchmark_original/"),
    ("raw", ""),
]

DEPRECATED_ROUTE = (
    "/dag/<string:idx>/_benchmark_original/",
    "dag_benchmark_original",
    DAGDetailEndpoint,
)


def _register_deprecated_routes(app):
    """
    The live app only routes DAGDetailEndpointRaw at /dag/<idx>/ now (see
    cornflow.endpoints.__init__). Register the deprecated Original
    implementation on a separate, benchmark-only path so this script can
    still compare it against the live one. Must run before `case.setUp()`
    (Flask locks `add_url_rule` after the first request).
    """
    url_rule, endpoint_name, view_class = DEPRECATED_ROUTE
    register_deprecated_route(
        app, url_rule, endpoint_name, view_class, view_class.ROLES_WITH_ACCESS
    )


def _grant_deprecated_permissions():
    """
    Grant GET permission for the benchmark-only route. Must run after
    `case.setUp()` (needs the `api_view`/`roles`/`actions` tables).
    """
    url_rule, endpoint_name, view_class = DEPRECATED_ROUTE
    grant_get_permission(url_rule, endpoint_name, view_class.ROLES_WITH_ACCESS)


def _build_large_payload(target_bytes):
    """Build a JSON-serializable dict that is at least `target_bytes` when dumped."""
    unit = {"idx": 0, "values": list(range(50)), "text": "x" * 500}
    unit_size = len(json.dumps(unit))
    count = max(1, target_bytes // unit_size)
    return {"rows": [{**unit, "idx": i} for i in range(count)]}


def _time_requests(client, url, headers, n):
    """
    Times `n` GETs against `url`. `db.session.remove()` is called before
    each request to force a fresh session, mirroring how a real deployment
    tears the session down at the end of every request (via Flask-SQLAlchemy's
    teardown_appcontext). Without this, the flask_testing harness keeps one
    long-lived session across all requests in a run, and the ORM path
    silently benefits from SQLAlchemy's identity-map caching of previously
    loaded rows -- an artifact that would not happen in production and that
    massively (and unfairly) skews a same-row, repeated-GET benchmark.
    """
    durations = []
    for i in range(n):
        db.session.remove()
        start = time.perf_counter()
        response = client.get(url, headers=headers, follow_redirects=True)
        durations.append(time.perf_counter() - start)
        if response.status_code != 200:
            raise RuntimeError(f"GET {url} returned {response.status_code}")
        print(f"    request {i + 1}/{n}: {durations[-1]:.3f}s")
    return durations


def _report(name, durations):
    print(f"\n{name}:")
    print(f"  min:    {min(durations):.3f}s")
    print(f"  mean:   {statistics.mean(durations):.3f}s")
    print(f"  median: {statistics.median(durations):.3f}s")
    if len(durations) > 1:
        print(f"  stdev:  {statistics.stdev(durations):.3f}s")
    print(f"  max:    {max(durations):.3f}s")


def run():
    case = TestExecutionsDetailEndpointMock()
    case._pre_setup()
    _register_deprecated_routes(case.app)
    case.setUp()
    _grant_deprecated_permissions()
    try:
        print(
            f"Building instance/execution payloads of ~{TARGET_BYTES / (1024 * 1024):.0f} MB each ..."
        )
        instance_data = _build_large_payload(TARGET_BYTES)
        execution_data = _build_large_payload(TARGET_BYTES)

        print("Saving instance and execution rows ...")
        instance = InstanceModel(
            dict(
                user_id=case.user.id,
                name="benchmark-instance",
                description="benchmark fixture",
                data=instance_data,
                schema=None,
            )
        )
        instance.save()

        execution = ExecutionModel(
            dict(
                user_id=case.user.id,
                instance_id=instance.id,
                name="benchmark-execution",
                description="benchmark fixture",
                data=execution_data,
                config={"solver": "cbc"},
                schema=None,
            )
        )
        execution.save()

        token = case.create_service_user()
        headers = case.get_header_with_auth(token)

        results = {}
        for name, url_suffix in VARIANTS:
            print(f"\nTiming {NUM_REQUESTS} requests against the {name} endpoint ...")
            url = f"{DAG_URL}{execution.id}/{url_suffix}"
            results[name] = _time_requests(case.client, url, headers, NUM_REQUESTS)

        for name, _ in VARIANTS:
            _report(name, results[name])

        baseline = statistics.mean(results["original"])
        print("\nSpeedup vs original (mean):")
        for name, _ in VARIANTS[1:]:
            speedup = baseline / statistics.mean(results[name])
            print(f"  {name}: {speedup:.2f}x")
    finally:
        case.tearDown()
        case._post_teardown()


if __name__ == "__main__":
    run()
