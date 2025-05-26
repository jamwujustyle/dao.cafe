import os
import tempfile
from .settings import *

# Override Redis host for tests
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")

# Override Redis cache configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379/1",
    }
}

# Override Celery broker URL
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:6379/0"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:6379/0"

# Use a temporary directory for media files during tests
MEDIA_ROOT = tempfile.mkdtemp()

# Disable permissions check for media directory
FILE_UPLOAD_DIRECTORY_PERMISSIONS = None
FILE_UPLOAD_PERMISSIONS = 0o644

# Disable throttling for tests to prevent 429 responses
REST_FRAMEWORK = REST_FRAMEWORK.copy()
REST_FRAMEWORK.update(
    {
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {},
    }
)
