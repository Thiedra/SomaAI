from pathlib import Path
from decouple import config, Csv
import dj_database_url

from datetime import timedelta
from celery.schedules import crontab
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,.railway.app", cast=Csv())
AUTH_USER_MODEL = "users.User"

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",  # ← add this for logout blacklisting
    "corsheaders",

]

LOCAL_APPS = [
    "users",
    "core",
    "simplifier",
    "quizzes",
    "progress",
    "planner",
    "career",
    "dashboard",
    "notifications",
    "homework",
    "community",
    "library",
    "ai_proxy",
    "games",
    "cloudinary",
    "cloudinary_storage",
    
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "soma_ai.urls"
# --- CORS (allow frontend dev server) ---
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://localhost:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "soma_ai.wsgi.application"

# --- Database ---
DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL", default="sqlite:///db.sqlite3")
    )
}

# --- Cache (Redis) ---
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

# --- Celery ---
CELERY_BROKER_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

# --- Swagger ---
SPECTACULAR_SETTINGS = {
    "TITLE": "Soma AI API",
    "DESCRIPTION": "AI-powered learning platform for African students.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "TAGS": [
        {"name": "Auth"},
        {"name": "Notes"},
        {"name": "Simplifier"},
        {"name": "Quizzes"},
        {"name": "Progress"},
        {"name": "Planner"},
        {"name": "Career"},
        {"name": "Dashboard"},
        {"name": "Homework"},
        {"name": "Assignments"},
        {"name": "Community"},
        {"name": "Library"},
        {"name": "AI Proxy"},
        {"name": "Games"},

    ],
}

# --- AI Keys ---
COHERE_API_KEY = config("COHERE_API_KEY", default="")


# --- Static / Media ---
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TIME_ZONE = "Africa/Kigali"
USE_I18N = True
USE_TZ = True

# --- Email ---
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="Soma AI <noreply@somaai.rw>")

# --- Celery Beat Schedule and Email configulation stuffs ---
CELERY_BEAT_SCHEDULE = {
    # every Monday at 8am Kigali time
    "weekly-student-summary": {
        "task": "notifications.tasks.send_all_weekly_student_summaries",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
    },
    "weekly-teacher-report": {
        "task": "notifications.tasks.send_all_weekly_teacher_reports",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
    },
    # every day at 7am — check for inactivity
    "daily-inactivity-check": {
        "task": "progress.tasks.check_inactivity_alerts",
        "schedule": crontab(hour=7, minute=0),
    },
    # every Monday at midnight — compute weekly snapshots
    "weekly-snapshots": {
        "task": "progress.tasks.compute_weekly_snapshots",
        "schedule": crontab(hour=0, minute=0, day_of_week=1),
    },
}

# --- Simple JWT ---
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

#configure cloudinary
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": config("CLOUDINARY_CLOUD_NAME", default=""),
    "API_KEY": config("CLOUDINARY_API_KEY", default=""),
    "API_SECRET": config("CLOUDINARY_API_SECRET", default=""),
}
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_ROOT = BASE_DIR / "staticfiles"