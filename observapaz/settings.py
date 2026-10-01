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
    # Límite de envíos anónimos del formulario público de casos, para que
    # no se pueda inundar la bandeja de "pendientes" con envíos masivos.
    # Solo se aplica a la creación de casos sin sesión iniciada (ver
    # CasoVictimizanteViewSet.get_throttles); no afecta lecturas ni a
    # usuarios ya logueados.
    "DEFAULT_THROTTLE_RATES": {
        "envio_caso": os.environ.get("THROTTLE_ENVIO_CASO", "20/hour"),
    },
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

# --- Endurecimiento de seguridad para producción con subdominios ---
#
# CSRF_TRUSTED_ORIGINS: obligatorio en Django 4+ para aceptar POST desde
# un origen distinto al que sirvió el formulario. Con 24 subdominios en
# juego, se define con comodín. Vacío por defecto -no cambia nada en
# desarrollo local-; en producción, en el .env:
#   CSRF_TRUSTED_ORIGINS=https://observapaz.org,https://*.observapaz.org
_csrf_trusted = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
if _csrf_trusted:
    CSRF_TRUSTED_ORIGINS = [origen.strip() for origen in _csrf_trusted.split(",") if origen.strip()]

# El servidor Django corre detrás de Nginx, que es quien de verdad habla
# HTTPS con el navegador y le pasa la petición a Gunicorn por HTTP simple.
# Esta línea le permite a Django reconocer, por la cabecera que reenvía
# Nginx, que la conexión original sí era HTTPS -sin ella, activar
# SECURE_SSL_REDIRECT provocaría un bucle infinito de redirecciones-.
# Es inofensiva por sí sola: no hace nada mientras Nginx no envíe esa
# cabecera y mientras las variables de abajo sigan en su valor por
# defecto (desactivadas).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Todo esto queda APAGADO por defecto a propósito, para no romper nada de
# lo que ya funciona (incluye el desarrollo local sin HTTPS). Se activa
# solo si lo pides explícitamente en el .env, y únicamente después de
# confirmar que Nginx ya está mandando "proxy_set_header X-Forwarded-Proto
# $scheme;" -si se activa sin eso, el sitio queda en un bucle de
# redirecciones-.
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "False") == "True"
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False") == "True"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False") == "True"
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0
