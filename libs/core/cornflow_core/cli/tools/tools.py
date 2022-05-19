# Shared
def generate_class_def(class_name, parent_class):
    return f'class {class_name}({", ".join(parent_class)}):\n'
