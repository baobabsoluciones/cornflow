"""
Benchmark comparing ``ExecutionDataEndpoint`` (full ORM object fetch,
DEPRECATED, no longer routed in the live app) against
``ExecutionDataEndpointRaw`` (raw-JSON-passthrough for ``data``/``checks``/
``kpis``, the live implementation routed at ``/execution/<idx>/data/``)
when ``execution.data`` is very large.

This is a standalone script, not a pytest test (the filename does not match
``test_*.py`` so it is never collected). It uses the Flask test client, so
timings reflect server-side (ORM + JSON (de)serialization) overhead rather
than network latency.

Run from ``cornflow-server``:

    python -m cornflow.tests.load.benchmark_execution_data_endpoint
"""

import statistics

from cornflow.endpoints.execution import ExecutionDataEndpoint
from cornflow.models import ExecutionModel, InstanceModel
from cornflow.shared import db
from cornflow.tests.custom_test_case import CustomTestCase
from cornflow.tests.const import EXECUTION_URL
from cornflow.tests.load.benchmark_dag_endpoint import (
    _build_large_payload,
    _report,
    _time_requests,
)
from cornflow.tests.load._deprecated_routes import (
    grant_get_permission,
    register_deprecated_route,
)

# Target size (bytes) of the execution.data JSON blob.
TARGET_BYTES = 100 * 1024 * 1024

# Number of timed GET requests per endpoint.
NUM_REQUESTS = 20

VARIANTS = [
    ("original", "_benchmark_original/"),
    ("raw", "data/"),
]

DEPRECATED_ROUTE = (
    "/execution/<string:idx>/_benchmark_original/",
    "execution_data_benchmark_original",
    ExecutionDataEndpoint,
)


def run():
    case = CustomTestCase()
    case._pre_setup()
    url_rule, endpoint_name, view_class = DEPRECATED_ROUTE
    register_deprecated_route(
        case.app, url_rule, endpoint_name, view_class, view_class.ROLES_WITH_ACCESS
    )
    case.setUp()
    grant_get_permission(url_rule, endpoint_name, view_class.ROLES_WITH_ACCESS)
    try:
        print(f"Building execution payload of ~{TARGET_BYTES / (1024 * 1024):.0f} MB ...")
        execution_data = _build_large_payload(TARGET_BYTES)

        print("Saving instance and execution rows ...")
        instance = InstanceModel(
            dict(
                user_id=case.user.id,
                name="benchmark-instance",
                description="benchmark fixture",
                data={"small": True},
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
                checks={"check_1": []},
                kpis={"kpi_1": 42},
                config={"solver": "cbc"},
                schema=None,
            )
        )
        execution.save()

        headers = case.get_header_with_auth(case.token)

        results = {}
        for name, url_suffix in VARIANTS:
            print(f"\nTiming {NUM_REQUESTS} requests against the {name} endpoint ...")
            url = f"{EXECUTION_URL}{execution.id}/{url_suffix}"
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
