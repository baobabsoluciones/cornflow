from ..schemas.json_factory import gen_schema, ParameterSchema, sort_dict


dict_params = \
    dict(
        CoefficientsSchema=[
            dict(name='name', type='String', required=True),
            dict(name='value', type='Float', required=True)],
         ObjectiveSchema=[
             dict(name='name', type='String', required=False, allow_none=True),
             dict(name='coefficients', type='CoefficientsSchema', many=True, required=True)],
         ConstraintSchema=[
             dict(name='name', type='String', required=True),
             dict(name='sense', type='Integer', required=True),
             dict(name='pi', type='Float', required=True, allow_none=True),
             dict(name='constant', type='Float', required=False, allow_none=True),
             dict(name='coefficients', type='CoefficientsSchema', many=True, required=True)
         ],
         VariableSchema = [
             dict(name='name', type='String', required=True),
             dict(name='lowBound', type='Float', allow_none=True),
             dict(name='upBound', type='Float', allow_none=True),
             dict(name='cat', type='String', required=True),
             dict(name='dj', type='Float', allow_none=True),
             dict(name='varValue', type='Float', allow_none=True)
         ],
         ParametersSchema=[
             dict(name='name', type='String', required=True),
             dict(name='sense', type='Integer', required=True),
             dict(name='status', type='Integer'),
             dict(name='sol_status', type='Integer')
         ],
         Sos1Constraints=[
             dict(name='placeholder', type='String', required=False),
         ],
         Sos2Constraints=[
             dict(name='placeholder', type='String', required=False),
         ],
         DataSchema=[
             dict(name='objective', type='ObjectiveSchema', required=True),
             dict(name='parameters', type='ParametersSchema', required=True),
             dict(name='constraints', type='ConstraintSchema', many=True, required=True),
             dict(name='variables', type='VariableSchema', many=True, required=True),
             dict(name='sos1', type='Sos1Constraints', many=True, required=True),
             dict(name='sos2', type='Sos2Constraints', many=True, required=True),
         ]
         )

result_dict = {}
ordered = sort_dict(dict_params)
tuplist = sorted(dict_params.items(), key=lambda v: ordered[v[0]])
for key, params in tuplist:
    schema = ParameterSchema()
    # this line validates the list of parameters:
    params1 = schema.load(params, many=True)
    result_dict[key] = gen_schema(key, params1, result_dict)

DataSchema = result_dict['DataSchema']