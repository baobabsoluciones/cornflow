"""
Benchmark comparing ``CaseDataEndpoint`` (full ORM object fetch,
DEPRECATED, no longer routed in the live app) against
``CaseDataEndpointRaw`` (raw-JSON-passthrough, the live implementation
routed at ``/case/<idx>/data/``) when both ``case.data`` and
``case.solution`` are very large.

Unlike the DAG/instance/execution raw endpoints, this one still decodes
``solution`` once (to compute the ``indicators`` field), so it is expected
to show a smaller speedup than those -- it only skips the decode+encode
round trip for ``data``/``checks``/``solution_checks``/``kpis``, and only
the encode half for ``solution``.

This is a standalone script, not a pytest test (the filename does not match
``test_*.py`` so it is never collected). It uses the Flask test client, so
timings reflect server-side (ORM + JSON (de)serialization) overhead rather
than network latency.

Run from ``cornflow-server``:

    python -m cornflow.tests.load.benchmark_case_data_endpoint
"""

import statistics

from cornflow.endpoints.case import CaseDataEndpoint
from cornflow.models import CaseModel
from cornflow.shared import db
from cornflow.tests.custom_test_case import CustomTestCase
from cornflow.tests.const import CASE_URL
from cornflow.tests.load.benchmark_dag_endpoint import (
    _build_large_payload,
    _report,
    _time_requests,
)
from cornflow.tests.load._deprecated_routes import (
    grant_get_permission,
    register_deprecated_route,
)

# Target size (bytes) of EACH of the case.data / case.solution JSON blobs.
TARGET_BYTES = 100 * 1024 * 1024

# Number of timed GET requests per endpoint.
NUM_REQUESTS = 20

VARIANTS = [
    ("original", "_benchmark_original/"),
    ("raw", "data/"),
]

DEPRECATED_ROUTE = (
    "/case/<int:idx>/_benchmark_original/",
    "case_data_benchmark_original",
    CaseDataEndpoint,
)


def run():
    case_test = CustomTestCase()
    case_test._pre_setup()
    url_rule, endpoint_name, view_class = DEPRECATED_ROUTE
    register_deprecated_route(
        case_test.app, url_rule, endpoint_name, view_class, view_class.ROLES_WITH_ACCESS
    )
    case_test.setUp()
    grant_get_permission(url_rule, endpoint_name, view_class.ROLES_WITH_ACCESS)
    try:
        print(
            f"Building case data/solution payloads of ~{TARGET_BYTES / (1024 * 1024):.0f} MB each ..."
        )
        case_data = _build_large_payload(TARGET_BYTES)
        case_solution = _build_large_payload(TARGET_BYTES)
        case_solution["indicators"] = {"cost": 123.4, "time": 5.6}

        print("Saving case row ...")
        case = CaseModel(
            dict(
                user_id=case_test.user.id,
                name="benchmark-case",
                description="benchmark fixture",
                data=case_data,
                checks={"check_1": []},
                solution=case_solution,
                solution_checks={"solution_check_1": []},
                kpis={"kpi_1": 42},
                schema=None,
            )
        )
        case.save()

        headers = case_test.get_header_with_auth(case_test.token)

        results = {}
        for name, url_suffix in VARIANTS:
            print(f"\nTiming {NUM_REQUESTS} requests against the {name} endpoint ...")
            url = f"{CASE_URL}{case.id}/{url_suffix}"
            results[name] = _time_requests(case_test.client, url, headers, NUM_REQUESTS)

        for name, _ in VARIANTS:
            _report(name, results[name])

        baseline = statistics.mean(results["original"])
        print("\nSpeedup vs original (mean):")
        for name, _ in VARIANTS[1:]:
            speedup = baseline / statistics.mean(results[name])
            print(f"  {name}: {speedup:.2f}x")
    finally:
        case_test.tearDown()
        case_test._post_teardown()


if __name__ == "__main__":
    run()
