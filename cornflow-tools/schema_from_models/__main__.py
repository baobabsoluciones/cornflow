# Import from libraries
import argparse

# Import from internal modules
from schema_generator import SchemaGenerator

parser = argparse.ArgumentParser(
    description="Generate a new schema based on a set of models"
)
parser.add_argument(
    "path", metavar="path", type=str, help="The absolute path to the JSONSchema"
)
parser.add_argument(
    "-op",
    "--output_path",
    metavar="path",
    type=str,
    nargs=1,
    help="The output path.",
    required=False,
)
parser.add_argument(
    "-i",
    "--ignore_files",
    nargs="+",
    metavar="file",
    help="Files that will be ignored (with the .py extension)."
    "__init__.py files are automatically ignored. Ex: 'instance.py'",
    required=False,
    type=str,
)
parser.add_argument(
    "-l",
    "--leave_bases",
    action='store_true',
    help="Use this option to leave the bases classes BaseDataModel, "
         "EmptyModel and TraceAttributes in the schema. By default, they will be deleted"
)
args = parser.parse_args()
path = args.path.replace("\\", "/")
output_path = None
if args.output_path:
    output_path = args.output_path[0].replace("\\", "/")

SchemaGenerator(
    path,
    output_path=output_path,
    ignore_files=args.ignore_files,
    leave_bases=args.leave_bases
).main()
