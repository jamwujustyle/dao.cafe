from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    "delete-dips-every-24-hours": {
        "task": "forum.tasks.dip_cleanup",
        "schedule": crontab(minute=0, hour=0),
        "args": (),
    },
}
