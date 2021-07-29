import json
import os


def load_json(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, "r") as f:
        content = json.load(f)
    return content
