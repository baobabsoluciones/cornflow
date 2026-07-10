from marshmallow import Schema, fields
from cornflow.shared.frontend_automation.base_frontend_groups import (
    BaseFrontendGroup,
    BaseFrontendTable,
    BaseFrontendSection,
)


class TestModelSchema(Schema):
    name = fields.Str(required=True)
    description = fields.Str(required=False)


TEST_MODEL_JSONSCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
    },
    "required": ["name"],
}


class FrontendTableWithoutGroup(BaseFrontendTable):
    """
    Frontend table not associated to a group
    """

    title = {"en": "Frontend Table 1", "es": "Tabla de Frontend 1"}
    icon = "mdi-table"
    frontend_group = None
    frontend_section = None
    order = 1
    schemas = None


class FrontendGroup(BaseFrontendGroup):
    """
    Example frontend group
    """

    name = "example_group"
    title = {"en": "Example Group", "es": "Grupo de Ejemplo"}
    icon = "mdi-folder"
    frontend_section = None
    order = 2


class FrontendTableWithGroup(BaseFrontendTable):
    """
    Frontend table associated to a group
    """

    title = {"en": "Frontend Table 2", "es": "Tabla de Frontend 2"}
    icon = None
    frontend_group = FrontendGroup
    frontend_section = None
    order = 3
    schemas = None


class FrontendSection(BaseFrontendSection):
    """
    Example frontend section
    """

    name = "example_section"
    title = {"en": "Example Section", "es": "Sección de Ejemplo"}
    icon = "mdi-view-dashboard"
    order = 4


class FrontendTableWithSection(BaseFrontendTable):
    """
    Frontend table associated to a section
    """

    title = {"en": "Frontend Table 3", "es": "Tabla de Frontend 3"}
    icon = None
    frontend_group = None
    frontend_section = FrontendSection
    order = 5
    schemas = None


class FrontendGroupWithSection(BaseFrontendGroup):
    """
    Frontend group associated to a section
    """

    name = "example_group_with_section"
    title = {"en": "Example Group with Section", "es": "Grupo de Ejemplo con Sección"}
    icon = "mdi-ferry"
    frontend_section = FrontendSection
    order = 6


class FrontendTableWithGroupAndSection(BaseFrontendTable):
    """
    Frontend table associated to a group and a section
    """

    title = {"en": "Frontend Table 4", "es": "Tabla de Frontend 4"}
    icon = None
    frontend_group = FrontendGroupWithSection
    frontend_section = None
    order = 7
    schemas = None


class FrontendTableWithSchemas(BaseFrontendTable):
    """
    Frontend table with a non-None schemas list
    """

    title = {"en": "Frontend Table 5", "es": "Tabla de Frontend 5"}
    icon = "mdi-database"
    frontend_group = None
    frontend_section = None
    schemas = ["solve_model_dag", "gc"]
    order = 8


class FrontendTableWithSchemaDag(BaseFrontendTable):
    title = {"en": "Table Schema DAG", "es": "Tabla Schema DAG"}
    icon = "mdi-cog"
    frontend_group = None
    frontend_section = None
    schemas = ["solve_model_dag"]
    order = 9


class FrontendTableWithSchemaTwoDag(BaseFrontendTable):
    title = {"en": "Table Schema 2 DAG", "es": "Tabla Schema 2 DAG"}
    icon = "mdi-cog"
    frontend_group = None
    frontend_section = None
    schemas = ["gc"]
    order = 10


class FrontendTableWithUnknownSchema(BaseFrontendTable):
    title = {"en": "Table Unknown Schema", "es": "Tabla Schema Desconocido"}
    icon = "mdi-alert"
    frontend_group = None
    frontend_section = None
    schemas = ["nonexistent_dag"]
    order = 11


class FrontendTableWithMixedSchemas(BaseFrontendTable):
    title = {"en": "Table Mixed Schemas", "es": "Tabla Schemas Mixtos"}
    icon = "mdi-mix"
    frontend_group = None
    frontend_section = None
    schemas = ["solve_model_dag", "nonexistent_dag"]
    order = 12
