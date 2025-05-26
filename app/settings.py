import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Load the appropriate .env file based on environment
# By default, load .env.development if no specific environment is set
env_file = os.environ.get("DJANGO_ENV_FILE", ".env.development")
load_dotenv(env_file)
print(f"Loaded environment from: {env_file}")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.environ.get("SECRET_KEY", "nosecrets")
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# Hosts configuration based on environment
if DEBUG:
    # Development hosts
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "192.168.0.106:8000"]
else:
    # Production hosts - comma-separated list from environment variable
    ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt",
    "corsheaders",
    "eth_auth",
    "core",
    "user",
    "dao",
    "forum",
    "django_celery_beat",
    "rest_framework_simplejwt.token_blacklist",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240

WSGI_APPLICATION = "app.wsgi.application"

# db
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("DB_HOST"),
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
    }
}


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

MEDIA_URL = "/media/"
MEDIA_ROOT = "/vol/web/media"

STATIC_URL = "/static/"
STATIC_ROOT = "/vol/web/static"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]
# Default primary key field type

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "core.User"

# Import default CORS headers
from corsheaders.defaults import default_headers

# CORS settings based on environment
if DEBUG:
    # Development origins
    CORS_ALLOWED_ORIGINS = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
else:
    # Production origins - comma-separated list from environment variable
    CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
CORS_ALLOW_CREDENTIALS = True

# Add Sentry headers to allowed CORS headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    'sentry-trace',
    'baggage',
]


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [  # Fixed typo in setting name
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    
    # Add throttling configuration
    "DEFAULT_THROTTLE_CLASSES": [
        "services.utils.throttle.UserBurstRateThrottle",
        "services.utils.throttle.UserSustainedRateThrottle",
        "services.utils.throttle.AnonBurstRateThrottle",
        "services.utils.throttle.AnonSustainedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Authenticated users
        "user_burst": "60/minute",     # Short-term burst limit
        "user_sustained": "1000/day",  # Long-term sustained limit
        
        # Anonymous users (IP-based)
        "anon_burst": "30/minute",     # Short-term burst limit
        "anon_sustained": "500/day",   # Long-term sustained limit
    },
}

# Hide browsable API in production
if not DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer",
    ]


######## REDIS CONFIG ########

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://redis:6379/1",
    }
}
######## DRF CONFIG ########

SPECTACULAR_SETTINGS = {
    "TITLE": "DAO API",
    "DESCRIPTION": "Documentation for Decentralized Autonomous Forum API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "COMPONENT_SPLIT_REQUEST": True,
    # Security scheme configuration
    "SECURITY": [{"Bearer": []}],
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Enter 'Bearer <JWT>' where <JWT> is your access token",
        }
    },
    "TAGS": [
        {"name": "auth", "description": "authentication related endpoints"},
        {"name": "user", "description": "user related endpoints"},
        {
            "name": "dao",
            "description": "dao related includes blockchain interaction, registration in database, and actions like retrieve list, create and update",
        },
        {
            "name": "refresh",
            "description": "syncronizes database entries with data from chain",
        },
        {
            "name": "dip",
            "description": "forum api for dip interaction specific to dao",
        },
        {
            "name": "thread",
            "description": "forum api for thread interaction specific to dao",
        },
        {
            "name": "dynamic",
            "description": "dynamic handling view for thread and dip replies",
        },
    ],
}


######## JWT TOKEN CONFIG ########

# JWT settings based on environment
if DEBUG:
    # Development JWT settings - long lifetimes for easier testing
    SIMPLE_JWT = {
        "ACCESS_TOKEN_LIFETIME": timedelta(minutes=360000),
        "REFRESH_TOKEN_LIFETIME": timedelta(days=1000),
        # "ROTATE_REFRESH_TOKENS": True,
        # "BLACKLIST_AFTER_ROTATION": True,
    }
else:
    # Production JWT settings - secure defaults
    SIMPLE_JWT = {
        "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
        "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
        "ROTATE_REFRESH_TOKENS": True,
        "BLACKLIST_AFTER_ROTATION": True,
    }


# celery confs
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"
CELERY_TIMEZONE = "UTC"

# Blockchain settings
BLOCKCHAIN_SCAN_BLOCK_RANGE = 100000  # Default number of blocks to scan for events

# HTTPS settings
# Tell Django to trust the X-Forwarded-Proto header from the proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Use the X-Forwarded-Host header from the proxy
USE_X_FORWARDED_HOST = True

# Use the X-Forwarded-Port header from the proxy
USE_X_FORWARDED_PORT = True

# Only needed if you want to redirect all HTTP to HTTPS at the Django level
# (nginx is already doing this, so it's optional)
SECURE_SSL_REDIRECT = False

# Initialize Sentry only in production (when DEBUG is False)
if not DEBUG:
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN", ""),  # Get DSN from environment variable
        integrations=[
            DjangoIntegration(),
        ],
        # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
        # Set environment name
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
    )

# Configure logging to filter out DisallowedHost errors in production
# This is only applied when not running tests
if not os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('test_settings'):
    import logging
    import django.core.exceptions
    
    # Custom filter to ignore DisallowedHost errors
    class IgnoreDisallowedHostFilter(logging.Filter):
        def filter(self, record):
            # Return False to ignore the log record if it's a DisallowedHost error
            return not (
                record.exc_info 
                and record.exc_info[0] == django.core.exceptions.DisallowedHost
            )
    
    # Logging configuration
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'ignore_disallowed_host': {
                '()': 'app.settings.IgnoreDisallowedHostFilter',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'filters': ['ignore_disallowed_host'],
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': True,
            },
            'django.security': {
                'handlers': ['console'],
                'level': 'INFO',
                'filters': ['ignore_disallowed_host'],
                'propagate': False,
            },
            'django.request': {
                'handlers': ['console'],
                'level': 'INFO',
                'filters': ['ignore_disallowed_host'],
                'propagate': False,
            },
        },
    }
