import time
from psycopg2 import OperationalError as Psycopg2Error
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """django command to wait for database"""

    def handle(self, *args, **kwargs):
        self.stdout.write("waiting for database")
        db_up = False
        while db_up is False:
            try:
                self.check(databases=["default"])
                db_up = True
            except (Psycopg2Error, OperationalError):
                self.stdout.write("database unavailable, waiting 1 sec")
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS("DATABASE AVAILABLE"))
