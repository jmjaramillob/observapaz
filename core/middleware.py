import re

from django.conf import settings

from .models import Observatorio


class ObservatorioSubdominioMiddleware:
    """
    Lee el host de la solicitud (ej. 'obs-007.observapaz.org') y, si el
    subdominio coincide con el código de un observatorio activo, lo
    deja disponible como request.observatorio para el resto de la
    solicitud. Si no hay coincidencia (dominio raíz, 'www', o un
    subdominio que no corresponde a ningún observatorio), queda en None.

    IMPORTANTE: esto es solo una ayuda de PRESENTACIÓN -qué formulario o
    tablero mostrar por defecto en ese subdominio-. NUNCA se usa para
    decidir qué datos privados puede ver alguien: el encabezado Host lo
    puede mandar cualquiera con solo cambiarlo, así que el control de
    acceso real sigue -y debe seguir siempre- anclado al PerfilUsuario
    de la cuenta que inició sesión (ver core/utils.py).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.observatorio = self._resolver_observatorio(request)
        return self.get_response(request)

    def _resolver_observatorio(self, request):
        host = request.get_host().split(":")[0].lower()
        base = settings.DOMINIO_BASE.lower()

        if host == base or host == f"www.{base}":
            return None
        if not host.endswith(f".{base}"):
            return None

        subdominio = host[: -(len(base) + 1)]
        if not subdominio or "." in subdominio:
            # Vacío, o más de un nivel (algo.obs-007.dominio): no es un
            # subdominio de observatorio válido.
            return None

        # "obs1", "obs24" u "obs-007" se traducen a "OBS-001", "OBS-024", "OBS-007"
        coincidencia = re.fullmatch(r"obs-?0*(\d{1,3})", subdominio)
        if coincidencia:
            codigo = f"OBS-{int(coincidencia.group(1)):03d}"
        else:
            codigo = subdominio
        return Observatorio.objects.filter(codigo__iexact=codigo, activo=True).first()
