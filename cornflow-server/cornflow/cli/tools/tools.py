# Shared
TYPE_PRIORITIES = ["array", "string", "number", "integer", "boolean"]


def generate_class_def(class_name, parent_class):
    return f'class {class_name}({", ".join(parent_class)}):\n'


def get_type(prop):
    """
    Translate json schema types into python type functions.
        ex: string -> str

    :param prop: str properties of the json schema.
    :return: a tuple with the main type (str) and nullable (bool)
    """
    nullable = False
    ty = prop["type"]
    fmt = prop.get("format", None)
    # manage list of types
    if isinstance(ty, list):
        if "null" in ty:
            nullable = True
        if any(t in TYPE_PRIORITIES for t in ty):
            ty = [t for t in TYPE_PRIORITIES if t in ty][0]
        else:
            raise ValueError("unknown type: " + str(ty))
    # manage format
    if ty == "string" and fmt in ["date", "datetime", "time"]:
        ty = fmt
    return ty, nullable
