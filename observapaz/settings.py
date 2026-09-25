"""
Configuración de Django para OBSERVAPAZ.
Base de datos única PostgreSQL/PostGIS (sin multi-tenant).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "clave-de-desarrollo-cambiar-en-produccion")

DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Dominio raíz del proyecto (sin protocolo ni subdominio), usado para
# reconocer los subdominios de cada observatorio -ej. si esto es
# "observapaz.org", entonces "obs-007.observapaz.org" se reconoce como
# el subdominio del observatorio con código "OBS-007"-.
# En desarrollo local, "localhost" (ver el truco del archivo hosts en
# el manual para probar subdominios en tu propia PC).
DOMINIO_BASE = os.environ.get("DOMINIO_BASE", "localhost")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",  # soporte PostGIS

    "rest_framework",
    "django_filters",

    "core",
    "panel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.ObservatorioSubdominioMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "observapaz.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "panel" / "templates"],
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

WSGI_APPLICATION = "observapaz.wsgi.application"

# Base de datos única (PostgreSQL + PostGIS). Sin esquemas por tenant.
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("DB_NAME", "observapaz"),
        "USER": os.environ.get("DB_USER", "observapaz"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "observapaz"),
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "panel" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
# En desarrollo (DEBUG=True) sirve directo desde las carpetas static/ de cada
# app, sin exigir un collectstatic previo cada vez que cambias un archivo.
WHITENOISE_USE_FINDERS = DEBUG
WHITENOISE_AUTOREFRESH = DEBUG

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_PERMISSION_CLASSES": [
        # Por defecto, cerrado: cada ViewSet abre explícitamente lo que
        # necesita (lectura pública, creación pública, etc.) en vez de
        # heredar un acceso amplio por accidente.
        "rest_framework.permissions.IsAuthenticated",
    ],
}

LOGIN_URL = "panel:login"
LOGIN_REDIRECT_URL = "panel:tablero"
LOGOUT_REDIRECT_URL = "panel:publico"

# --- Correo (alertas al gestor cuando llega un registro pendiente) ---
# Por defecto usa el backend de "consola": en vez de enviar el correo de
# verdad, lo imprime en los logs del contenedor. Así nada se rompe si
# todavía no has configurado un servidor SMTP real. Para enviar correos
# de verdad, define estas variables en tu .env (ver .env.example).
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "OBSERVAPAZ <no-responder@observapaz.org>"
)

# URL base del sitio, para armar el enlace que va dentro del correo de
# alerta (ej. "https://observapaz.org" en producción).
SITIO_URL_BASE = os.environ.get("SITIO_URL_BASE", "http://localhost:8010")

# --- Conexión con ODK Central (servidor aparte, ver el manual de
# instalación) para traer los envíos hechos offline desde ODK Collect. ---
ODK_CENTRAL_URL = os.environ.get("ODK_CENTRAL_URL", "")
ODK_CENTRAL_EMAIL = os.environ.get("ODK_CENTRAL_EMAIL", "")
ODK_CENTRAL_PASSWORD = os.environ.get("ODK_CENTRAL_PASSWORD", "")
ODK_CENTRAL_PROJECT_ID = os.environ.get("ODK_CENTRAL_PROJECT_ID", "")

# Si se define, la sesión (y el token CSRF) quedan válidos en todos los
# subdominios a la vez -ej. ".observapaz.org"-, para que alguien pueda
# iniciar sesión en su propio subdominio de observatorio y seguir
# logueado si navega al dominio raíz, o viceversa. Vacío = cada
# subdominio maneja su propia sesión por separado (más simple, pero
# tocaría iniciar sesión de nuevo en cada uno).
_cookie_domain = os.environ.get("COOKIE_DOMINIO_COMPARTIDO", "")
if _cookie_domain:
    SESSION_COOKIE_DOMAIN = _cookie_domain
    CSRF_COOKIE_DOMAIN = _cookie_domain
