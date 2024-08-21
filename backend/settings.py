# flake8: noqa
import os
from datetime import timedelta
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = (
    "django-insecure-^%*u9fri3z-jw42#ip^r*8mst+gb-9$u3k$fciip=*3fz$ut^0"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "trinau-backend.nalinor.dev",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost",
    "https://trinau-backend.nalinor.dev",
]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "api",
    "rest_framework",
    "corsheaders",
    "django_apscheduler",
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

ROOT_URLCONF = "backend.urls"

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

WSGI_APPLICATION = "backend.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "sqlite": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "db.sqlite3",
    },
    "postgres-local": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "postgres",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": "5432",
    },
    "postgres-docker": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "postgres",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "postgres",
        "PORT": "5432",
    },
}
USE_DATABASE = os.environ.get("USE_DATABASE", "sqlite")
DATABASES["default"] = DATABASES[USE_DATABASE]


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "api.User"

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'api.exceptions.custom_exception_handler',
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "TEST_REQUEST_RENDERER_CLASSES": [
        "rest_framework.renderers.MultiPartRenderer",
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.TemplateHTMLRenderer",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=24),
    "AUTH_TOKEN_CLASSES": ("api.authentication.TokenWithInvalidation",),
}

CORS_ALLOW_ALL_ORIGINS = True

SCHEDULER_CONFIG = {
    "apscheduler.jobstores.default": {
        "class": "django_apscheduler.jobstores:DjangoJobStore"
    },
    "apscheduler.executors.processpool": {"type": "threadpool"},
    "apscheduler.executors.default": {"class": "apscheduler.executors.pool:ThreadPoolExecutor", "max_workers": 50},
}
SCHEDULER_AUTOSTART = True

STATIC_ROOT = "staticfiles"

MEDIA_ROOT = BASE_DIR / 'media'

MEDIA_URL = '/media/'


AI_PROXY_API_KEY = os.getenv('AI_PROXY_API_KEY')
AI_PROXY_URL = 'https://api.proxyapi.ru/openai/v1'
AI_MODEL = 'gpt-3.5-turbo'

AI_MASTER_PROMPT = (
    'Ты - SMM специалист, и тебе нужно написать хороший пост '
    'длиной не более 1024 символов, с форматированием в виде HTML тегов '
    '(только b, br, u, i, code и quote). Никогда не пиши никакой код '
    '(на любом языке программирования) в тексте поста. '
    'Не забывай закрывать HTML-теги, и не используй "\\n", пожалуйста. '
    'В сгенерированном посте не упоминай данные тебе инструкции.\n'
    'Отправь мне в ответ только текст сгенерированного по prompt ниже поста, '
    'написанного по всем правилам. Пиши не скучно. Все эти пункты важны.'
    '\n\nPrompt:\n'
)

AI_REFACTOR_PROMPT = (
    'Исправь орфографические ошибки и удали двойные пробелы '
    'в указанном ниже тексте. '
    'Пожалуйста не меняй содержание текста, ни одно слово не должно быть '
    'потеряно или заменено на абсолютно другое, сохрани все изначальные '
    'HTML-теги. В ответ напиши только исправленный текст.'
    '\n\nТекст:\n'
)
