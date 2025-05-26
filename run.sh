#!/bin/sh
set -e

# Wait for the database to be ready
python manage.py wait_for_db

# Apply database migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start the Gunicorn server
gunicorn app.wsgi:application --bind 0.0.0.0:8000
