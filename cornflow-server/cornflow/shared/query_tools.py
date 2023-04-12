from sqlalchemy import tuple_


def get_combinations(model, schema, fields, combinations, max_query=2000):
    """
    Get data from a table filtering it by a combination of fields.
    For large tables, the model should define an index to increase query speed:
        __table_args__ = (db.Index("ix_combinations", "field_1", "field_2"))
    :param model: data model of the table.
    :param schema: data schema of the table.
    :param fields: fields of the combinations
    :param combinations: values of the combinations as a list of tuples
    :param max_query: max length of combinations to query at the same time (databases are limited to a few thousands).
    :return: data as a list of dict.
    """
    model_fields = [getattr(model, f) for f in fields]
    n = len(combinations)
    n_query = 1 + n // max_query
    result = []
    for i in range(n_query):
        comb = combinations[i * max_query : min((i + 1) * max_query, n)]
        # print(f"Querying combinations in model {model}: batch {i}")
        condition = tuple_(*model_fields).in_(comb)
        query = model.query.filter(condition).all()
        ri = schema().dump(query, many=True)
        result += ri
    return result
