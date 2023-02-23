# Shared
def generate_class_def(class_name, parent_class):
    return f'class {class_name}({", ".join(parent_class)}):\n'


def get_main_type(str_type):
    """
    Translate json schema types into python type functions.
        ex: string -> str

    :param str_type: str type to be formatted
    :return: a python type function (str, int, float or bool)
    """
    type_priorities = ["array", "string", "number", "integer", "boolean"]
    if isinstance(str_type, str):
        return str_type
    if isinstance(str_type, list):
        for t in type_priorities:
            if t in str_type:
                return t
    raise ValueError("unknown type: " + str(str_type))