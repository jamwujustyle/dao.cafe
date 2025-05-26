from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

default = os.environ.get("DJANGO_SETTINGS_MODULE")

app = Celery("app")

app.config_from_object("django.conf:settings", namespace="CELERY")

from .celerybeat_schedule import CELERYBEAT_SCHEDULE

app.conf.beat_schedule = CELERYBEAT_SCHEDULE

app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"request: {self.request!r}")
