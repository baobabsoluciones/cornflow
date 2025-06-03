import sys
from importlib import import_module


def register_roles_command(external_app: str = None, verbose: bool = True):

    from sqlalchemy.exc import DBAPIError, IntegrityError
    from flask import current_app

    from cornflow.models import RoleModel
    from cornflow.shared.const import ROLES_MAP
    from cornflow.shared import db

    # Obtener resources_to_register usando el mismo patrón que permissions.py
    if external_app is None:
        from cornflow.endpoints import resources, alarms_resources

        resources_to_register = resources
        if current_app.config["ALARMS_ENDPOINTS"]:
            resources_to_register = resources + alarms_resources
    else:
        try:
            sys.path.append("./")
            external_module = import_module(external_app)
            resources_to_register = external_module.endpoints.resources
        except Exception as e:
            resources_to_register = []
            if verbose:
                current_app.logger.warning(
                    f"Could not load resources from external app {external_app}: {e}"
                )

    roles_registered = [role.name for role in RoleModel.get_all_objects()]

    # Registrar roles de ROLES_MAP (roles base de Cornflow)
    roles_to_register = [
        RoleModel({"id": key, "name": value})
        for key, value in ROLES_MAP.items()
        if value not in roles_registered
    ]

    # Extraer roles custom de ROLES_WITH_ACCESS de todos los endpoints
    custom_role_ids = set()

    for view in resources_to_register:
        if hasattr(view["resource"], "ROLES_WITH_ACCESS"):
            for role_id in view["resource"].ROLES_WITH_ACCESS:
                # TODO: Utilizar todos los ids de la bbdd en vez de ROLES_MAP.keys()
                if role_id not in ROLES_MAP.keys():  # Solo roles custom
                    custom_role_ids.add(role_id)

    # Crear roles custom encontrados
    for role_id in custom_role_ids:
        # Crear rol con ID, el nombre se generará automáticamente como custom_role_<id>
        temp_role = RoleModel({"id": role_id})

        if temp_role.name not in roles_registered:
            roles_to_register.append(temp_role)

    if verbose and len(custom_role_ids) > 0:
        current_app.logger.info(f"Custom roles found: {sorted(custom_role_ids)}")

    if len(roles_to_register) > 0:
        db.session.bulk_save_objects(roles_to_register)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error on roles register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknown error on roles register: {e}")

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('roles', 'id'), MAX(id)) FROM roles;"
        )
        try:
            db.session.commit()
        except DBAPIError as e:
            db.session.rollback()
            current_app.logger.error(f"Unknown error on roles sequence updating: {e}")

    if verbose:
        if len(roles_to_register) > 0:
            current_app.logger.info(f"Roles registered: {roles_to_register}")
        else:
            current_app.logger.info("No new roles to be registered")

    return True
