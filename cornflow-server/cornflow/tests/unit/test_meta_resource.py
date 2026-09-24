"""
Unit tests for the BaseMetaResource class.

This module contains tests for the logic that all the resources share, and that no
endpoint of cornflow exposes on its own: the bulk update. The endpoints that use it
are the ones that the cli generates (`put_bulk`), so the resource is built here the
same way `cli/tools/endpoint_tools.py` builds it.

Classes
-------
TestPostBulkUpdate
    Tests for the bulk update on a model with soft delete
TestPostBulkUpdateNoSoftDelete
    Tests for the bulk update on a model without soft delete
TestPostBulkUpdateClientId
    Tests for the bulk update on the models that take the id from the payload
"""

# Imports from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import AlarmsModel, RoleModel, ViewModel
from cornflow.shared.exceptions import InvalidData
from cornflow.tests.custom_test_case import CustomTestCase


class BulkUpdateTestCase(CustomTestCase):
    """
    Base test case that builds a resource on top of a model and sends rows to its
    bulk update.
    """

    # the model the resource works on, set by each test case
    data_model = None

    def setUp(self):
        super().setUp()
        self.model = self.data_model
        self.resource = BaseMetaResource()
        self.resource.data_model = self.data_model
        # the id is what the generated endpoints use as unique
        self.resource.unique = ["id"]
        # the bulk update tracks the user that sends the rows, but there is no request
        # on these tests, so the user is given directly
        self.resource.get_user_id = lambda: self.user.id

    def bulk_update(self, rows):
        """
        Sends a list of rows to the bulk update of the resource

        :param list rows: the rows to create or update
        :return: the message and the status code returned by the resource
        :rtype: Tuple(dict, integer)
        """
        return self.resource.post_bulk_update(data={"data": rows})


class TestPostBulkUpdate(BulkUpdateTestCase):
    """
    Test cases for the bulk update on :class:`AlarmsModel`, a model with soft delete
    whose id is given by the database.
    """

    data_model = AlarmsModel

    def create_alarm(self, name, criticality=1, description="Description"):
        """
        Creates one alarm directly on the database

        :param str name: the name of the alarm
        :param float criticality: the criticality of the alarm
        :param str description: the description of the alarm
        :return: the created alarm
        :rtype: :class:`AlarmsModel`
        """
        alarm = AlarmsModel(
            {"name": name, "criticality": criticality, "description": description}
        )
        alarm.save()
        return alarm

    def test_update_existing_row(self):
        """
        A row that exists and is not deleted gets updated
        """
        alarm = self.create_alarm("Alarm 1")

        _, status = self.bulk_update(
            [
                {
                    "id": alarm.id,
                    "name": "Alarm 1 edited",
                    "criticality": 2,
                    "description": "Description",
                }
            ]
        )

        self.assertEqual(201, status)
        self.assertEqual(1, AlarmsModel.query.count())
        self.assertEqual(
            "Alarm 1 edited", AlarmsModel.get_one_object(idx=alarm.id).name
        )

    def test_new_row_is_created(self):
        """
        A row whose id does not exist yet gets created, and the rows that are already
        on the table are left alone
        """
        kept = self.create_alarm("Alarm 1", description="Keep me")

        _, status = self.bulk_update(
            [
                {
                    "id": kept.id + 100,
                    "name": "Alarm 2",
                    "criticality": 1,
                    "description": "Description",
                }
            ]
        )

        self.assertEqual(201, status)
        self.assertEqual(2, AlarmsModel.get_all_objects().count())
        self.assertEqual("Keep me", AlarmsModel.get_one_object(idx=kept.id).description)

    def test_soft_deleted_row_is_reactivated(self):
        """
        A row that was soft deleted and is matched by the unique fields is
        reactivated: its deleted_at is cleared and it is updated with the data sent,
        instead of a new row being created
        """
        self.resource.unique = ["name"]
        deleted = self.create_alarm("Alarm 1", description="Deleted one")
        deleted.disable()

        # the row is not visible on the reads any more
        self.assertEqual(0, AlarmsModel.get_all_objects().count())

        _, status = self.bulk_update(
            [{"name": "Alarm 1", "criticality": 2, "description": "Resent"}]
        )

        self.assertEqual(201, status)
        reactivated = AlarmsModel.query.get(deleted.id)
        self.assertIsNone(reactivated.deleted_at)
        self.assertEqual("Resent", reactivated.description)
        # and it is visible on the reads again
        visible = AlarmsModel.get_all_objects().all()
        self.assertEqual(1, len(visible))
        self.assertEqual(deleted.id, visible[0].id)


class TestPostBulkUpdateNoSoftDelete(BulkUpdateTestCase):
    """
    Test cases for the bulk update on :class:`ViewModel`, that inherits from
    EmptyBaseModel and therefore has no deleted_at column.
    """

    data_model = ViewModel

    def test_update_existing_row(self):
        """
        A model without soft delete keeps updating the row that already exists
        """
        view = ViewModel.query.first()

        _, status = self.bulk_update(
            [
                {
                    "id": view.id,
                    "name": view.name,
                    "url_rule": view.url_rule,
                    "description": "edited description",
                }
            ]
        )

        self.assertEqual(201, status)
        self.assertEqual("edited description", ViewModel.query.get(view.id).description)

    def test_new_row_is_created(self):
        """
        A model without soft delete keeps creating the rows that do not exist
        """
        count = ViewModel.query.count()

        _, status = self.bulk_update(
            [{"id": 10000, "name": "brand new view", "url_rule": "/brand-new/"}]
        )

        self.assertEqual(201, status)
        self.assertEqual(count + 1, ViewModel.query.count())
        self.assertEqual(1, ViewModel.query.filter_by(name="brand new view").count())


class TestPostBulkUpdateClientId(BulkUpdateTestCase):
    """
    Test cases for the bulk update on the models that take the id from the payload,
    the same way the models that the cli generates do.
    """

    data_model = RoleModel

    def test_id_of_a_soft_deleted_row_is_reactivated(self):
        """
        The id of a soft deleted row can be given again to the bulk update: the row
        that holds it is reactivated and updated with the data sent, instead of
        failing on the primary key or being left deleted
        """
        deleted = RoleModel({"id": 99, "name": "a role"})
        deleted.save()
        deleted.disable()

        _, status = self.bulk_update([{"id": 99, "name": "a role resent"}])

        self.assertEqual(201, status)
        reactivated = RoleModel.query.get(99)
        self.assertIsNone(reactivated.deleted_at)
        self.assertEqual("a role resent", reactivated.name)
        # and it is visible on the reads again
        self.assertIsNotNone(RoleModel.get_one_object(idx=99))

    def test_id_of_a_live_row_is_not_rejected(self):
        """
        An id held by a row that is not deleted is not the case that is rejected: it
        keeps failing on the primary key, the way it did before
        """
        live = RoleModel({"id": 98, "name": "a live role"})
        live.save()
        self.resource.unique = ["name"]

        with self.assertRaises(InvalidData):
            self.bulk_update([{"id": 98, "name": "another role"}])

        self.assertEqual("a live role", RoleModel.query.get(98).name)
