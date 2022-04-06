# Import from libraries
import argparse

# Import from internal modules
from api_generator import APIGenerator

parser = argparse.ArgumentParser(
    description="Generate new endpoints, models and schemas from a JSONSchema."
)
parser.add_argument(
    "path", metavar="path", type=str, help="The absolute path to the JSONSchema"
)
parser.add_argument(
    "app_name", metavar="name", type=str, help="The name of the application."
)
parser.add_argument(
    "-op",
    "--output_path",
    type=str,
    nargs="?",
    help="The output path.",
    required=False,
    default="output",
)
options = ["getOne", "getAll", "update", "deleteOne", "deleteAll"]
parser.add_argument(
    "--remove_methods",
    nargs="*",
    help="Methods that will NOT be added to the new endpoints.",
    required=False,
    type=str,
    choices=options,
)
parser.add_argument(
    "--one",
    type=str,
    required=False,
    help="If your schema describes only one table, use this option to indicate the name of the table.",
    nargs=1,
)

args = parser.parse_args()
path = args.path.replace("\\", "/")

if args.remove_methods is not None:
    methods_to_add = list(set(options) - set(args.remove_methods))
else:
    methods_to_add = []

one_table = False
name_table = None
if args.one:
    one_table = True
    name_table = args.one[0]

APIGenerator(
    path,
    app_name=args.app_name,
    output_path=args.output_path,
    options=methods_to_add,
    one_table=one_table,
    name_table=name_table,
).main()
