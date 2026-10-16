from django.conf import settings


def enlaces_pie(request):
    """Enlaces del pie de página; si no están configurados, no se muestran."""
    return {
        "soporte_email": settings.SOPORTE_EMAIL,
        "politica_privacidad_url": settings.POLITICA_PRIVACIDAD_URL,
    }
