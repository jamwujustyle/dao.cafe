from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule


class Command(BaseCommand):
    help = "creates a periodic task to clean up old dips every 24 hours"

    def handle(self, *args, **kwargs):
        self.stdout.write("waiting for celery-beat")
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.DAYS,
        )

        PeriodicTask.objects.get_or_create(
            interval=schedule,
            name="delete dips every 24 hours",
            task="forum.tasks.dip_cleanup",
        )
        self.stdout.write(self.style.SUCCESS("PERIODIC TASK CREATED SUCCESSFULLY"))
