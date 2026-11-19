"""
Shared helper for the benchmark scripts in this package.

The live app only routes the ``*Raw`` endpoint implementations now (see
``cornflow.endpoints.__init__``) -- the deprecated Original/Fast classes
are no longer wired up there. To let the benchmark scripts still compare
all variants side by side, this module registers the deprecated classes
on extra, benchmark-only URLs directly on the test app, and grants them
the same GET permission the old routes used to carry (cornflow's
`@authenticate` decorator checks a DB-backed ``ViewModel`` /
``PermissionViewRoleModel`` pair per request, keyed by the exact
``url_rule`` string -- it isn't satisfied by the resource's static
``ROLES_WITH_ACCESS`` list alone).
"""

from cornflow.models import PermissionViewRoleModel, ViewModel
from cornflow.shared.const import GET_ACTION


def register_deprecated_route(app, url_rule, endpoint_name, view_class, roles):
    """
    Add a benchmark-only Flask route for a deprecated (unrouted) resource
    class, and grant it GET permission for `roles`.

    Must be called after `TestCase._pre_setup()` (so `app` exists) but
    before the first request is dispatched (Flask locks `add_url_rule`
    after that) -- i.e. before `TestCase.setUp()`.

    :param app: the Flask app (`case.app` after `_pre_setup()`)
    :param str url_rule: the URL pattern to register, e.g.
      ``"/dag/<string:idx>/_benchmark_original/"``
    :param str endpoint_name: a unique Flask endpoint name for this route
    :param view_class: the deprecated `flask_restful.Resource` subclass
    :param list roles: role IDs to grant GET access to (typically the
      deprecated class's own `ROLES_WITH_ACCESS`)
    """
    app.add_url_rule(url_rule, view_func=view_class.as_view(endpoint_name))
    return url_rule, endpoint_name, roles


def grant_get_permission(url_rule, endpoint_name, roles):
    """
    Insert the `ViewModel` / `PermissionViewRoleModel` rows needed for
    `@authenticate` to allow GET requests to `url_rule` for `roles`.

    Must be called after `TestCase.setUp()` (so the `api_view`/`roles`/
    `actions` tables exist).
    """
    view = ViewModel.get_one_by_name(endpoint_name)
    if view is None:
        view = ViewModel(
            dict(
                name=endpoint_name,
                url_rule=url_rule,
                description=f"Benchmark-only route for {endpoint_name}",
            )
        )
        view.save()
    for role in roles:
        if not PermissionViewRoleModel.get_permission(
            role_id=role, api_view_id=view.id, action_id=GET_ACTION
        ):
            PermissionViewRoleModel(
                dict(action_id=GET_ACTION, api_view_id=view.id, role_id=role)
            ).save()
