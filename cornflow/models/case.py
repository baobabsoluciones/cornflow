"""
Model for the cases
"""

# Import from libraries
import jsonpatch
from sqlalchemy.dialects.postgresql import JSON

# Import from internal modules
from .meta_model import BaseDataModel
from ..shared.exceptions import InvalidPatch
from ..shared.utils import db, hash_json_256


# Originally inspired by this:
# https://docs.sqlalchemy.org/en/13/_modules/examples/materialized_paths/materialized_paths.html
# An alternative implementation with fixed width strings and no separator
# https://stackoverflow.com/questions/7276119/querying-sqlite-tree-structure

# this was use to get the ascendants. but requires postgres
# we would have to implement our own

# from sqlalchemy import func
# from sqlalchemy import select
# from sqlalchemy.dialects.postgresql import ARRAY
# from sqlalchemy.sql.expression import cast


SEPARATOR = "/"
# LENGTH_STR = 5


class CaseModel(BaseDataModel):
    __tablename__ = "cases"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    path = db.Column(db.String(500), nullable=False, index=True)
    # To find the descendants of this node, we look for nodes whose path
    # starts with this node's path.
    # c_path =
    descendants = db.relationship(
        "CaseModel",
        viewonly=True,
        order_by=path,
        primaryjoin=db.remote(db.foreign(path)).like(
            path.concat(id).concat(SEPARATOR + "%")
        ),
    )
    solution = db.Column(JSON, nullable=True)
    solution_hash = db.Column(db.String(256), nullable=False)

    # TODO: maybe implement this while making it compatible with sqlite:
    # Finding the ancestors is a little bit trickier. We need to create a fake
    # secondary table since this behaves like a many-to-many join.
    # secondary = select(
    #     [
    #         id.label("id"),
    #         func.unnest(
    #             cast(
    #                 func.string_to_array(
    #                     func.regexp_replace(path, r"\{}?\d+$".format(SEPARATOR), ""), "."
    #                 ),
    #                 ARRAY(Integer),
    #             )
    #         ).label("ancestor_id"),
    #     ]
    # ).alias()
    # ancestors = relationship(
    #     "CaseModel",
    #     viewonly=True,
    #     secondary=secondary,
    #     primaryjoin=id == secondary.c.id,
    #     secondaryjoin=secondary.c.ancestor_id == id,
    #     order_by=path,
    # )

    @property
    def depth(self):
        return len(self.path.split(SEPARATOR))

    def __init__(self, data, parent=None):
        super().__init__(data)
        if parent is None:
            # No parent: we set to empty path
            self.path = ""
        elif parent.path == "":
            # first level has empty path
            self.path = str(parent.id) + SEPARATOR
        else:
            # we compose the path with its parent
            self.path = parent.path + str(parent.id) + SEPARATOR

        self.solution = data.get("solution", None)
        self.solution_hash = hash_json_256(self.solution)

    def patch(self, data):
        """
        Method to patch the case

        :param dict data: the patches to apply.
        """
        if "data_patch" in data:
            self.data, self.data_hash = self.apply_patch(self.data, data["data_patch"])
        if "solution_patch" in data:
            self.solution, self.solution_hash = self.apply_patch(
                self.solution, data["solution_patch"]
            )

        self.user_id = data.get("user_id")
        super().update(data)

    def delete(self):
        children = [n for n in self.descendants]
        for n in children:
            n.delete()
        super().delete()

    @staticmethod
    def apply_patch(original_data, data_patch):
        """
        Helper method to apply the patch and calculate the new hash

        :param  dict original_data: the dict with the original data
        :param list data_patch: the list with the patch operations to perform
        :return: the patched data and the hash
        :rtype: Tuple(dict, str)
        """
        try:
            patched_data = jsonpatch.apply_patch(original_data, data_patch)
        except jsonpatch.JsonPatchConflict:
            raise InvalidPatch()
        except jsonpatch.JsonPointerException:
            raise InvalidPatch()
        return patched_data, hash_json_256(patched_data)

    def move_to(self, new_parent):
        new_path = new_parent.path + str(new_parent.id) + SEPARATOR
        for n in self.descendants:
            n.path = new_path + n.path[len(self.path) :]
        self.path = new_path

    def __repr__(self):
        return "<Case {}. Path: {}>".format(self.id, self.path)
