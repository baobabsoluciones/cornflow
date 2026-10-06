from marshmallow import fields, Schema


class DeployedDAGSchema(Schema):
    """"""

    id = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    instance_schema = fields.Raw(required=True, allow_none=False)
    solution_schema = fields.Raw(required=True, allow_none=False)
    config_schema = fields.Raw(required=True, allow_none=False)
    instance_checks_schema = fields.Raw(required=True, allow_none=False)
    solution_checks_schema = fields.Raw(required=True, allow_none=False)
    kpis_schema = fields.Raw(required=True, allow_none=False)


class DeployedDAGPostResponse(DeployedDAGSchema):
    """
    Response of the POST of a deployed DAG.
    permissions_warning is only present when the DAG has been saved
    but its permissions could not be created.
    """

    permissions_warning = fields.Str(required=False)


class DeployedDAGEditSchema(Schema):
    description = fields.Str(required=False, allow_none=True)
    instance_schema = fields.Raw(required=False)
    solution_schema = fields.Raw(required=False)
    config_schema = fields.Raw(required=False)
    instance_checks_schema = fields.Raw(required=True, allow_none=False)
    solution_checks_schema = fields.Raw(required=True, allow_none=False)
    kpis_schema = fields.Raw(required=True, allow_none=False)
