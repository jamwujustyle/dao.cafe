"""
test custom django management commands
"""

from unittest.mock import patch
from psycopg2 import OperationalError as Psycopg2Error

from django.core.management import call_command
from django.db.utils import OperationalError
from django.test import SimpleTestCase


@patch("core.management.commands.wait_for_db.Command.check")
class CommandTests(SimpleTestCase):
    """test django commands such as waiting for db and celery scheduler

    Args:
        SimpleTestCase (Class): django built in class
    """

    def test_wait_for_db_ready(self, patched_check):
        """test waiting for database"""
        patched_check.return_value = True

        call_command("wait_for_db")

        patched_check.assert_called_once_with(databases=["default"])

    @patch("time.sleep")
    def test_wait_for_db_delay(self, patched_sleep, patched_check):
        """test waiting for database when getting OperationalError"""
        patched_check.side_effect = (
            [Psycopg2Error] * 2 + [OperationalError] * 3 + [True]
        )

        call_command("wait_for_db")

        self.assertEqual(patched_check.call_count, 6)
        patched_check.assert_called_with(databases=["default"])

    @patch("django_celery_beat.models.PeriodicTask.objects.get_or_create")
    @patch("django_celery_beat.models.IntervalSchedule.objects.get_or_create")
    def test_create_periodic_task(
        self, mocked_interval_get_or_create, mocked_task_get_or_create, mock_schedule
    ):
        # mock_schedule = patch("django_celery_beat.models.IntervalSchedule").start()
        mock_schedule.DAYS = "days"
        mocked_interval_get_or_create.return_value = (mock_schedule, True)
        mocked_task_get_or_create.return_value = (None, True)

        call_command("create_periodic_task")

        mocked_interval_get_or_create.assert_called_once_with(
            every=1, period=mock_schedule.DAYS
        )
        mocked_task_get_or_create.assert_called_once_with(
            interval=mock_schedule,
            name="delete dips every 24 hours",
            task="forum.tasks.dip_cleanup",
        )
