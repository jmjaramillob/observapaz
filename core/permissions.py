from rest_framework import permissions


class SoloLecturaPublicaPermiso(permissions.BasePermission):
    """
    Lectura (GET) abierta a cualquiera -incluido sin login-, porque es
    información no sensible (observatorios, tipos de hecho).
    Crear/editar/borrar solo lo puede hacer personal (staff) desde el admin.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class CasoVictimizantePermiso(permissions.BasePermission):
    """
    - 'create' (el formulario público envía aquí su caso) y 'resumen'
      (cifras agregadas para el tablero público): abiertos a cualquiera.
    - Todo lo demás -listar o ver el detalle de un caso, que incluye
      descripción, fuente, cifras de población- requiere sesión
      iniciada. El alcance por observatorio se aplica en
      get_queryset() del ViewSet, no aquí.
    """

    def has_permission(self, request, view):
        if view.action in ("create", "resumen"):
            return True
        return bool(request.user and request.user.is_authenticated)


class SoloAutenticadoPermiso(permissions.BasePermission):
    """Todo requiere sesión iniciada (ej. los envíos crudos de ODK)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
