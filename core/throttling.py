from rest_framework.throttling import AnonRateThrottle


class EnvioCasoThrottle(AnonRateThrottle):
    """
    Límite de envíos del formulario público de casos por IP, sin sesión
    iniciada. No afecta a usuarios autenticados (ellos no pasan por este
    throttle) ni a ninguna lectura (tableros, resumen, listados): solo se
    aplica a la creación de un caso nuevo desde el formulario público
    -ver CasoVictimizanteViewSet.get_throttles-.

    La tasa se controla con THROTTLE_ENVIO_CASO en el .env (por defecto
    20 envíos por hora por IP).
    """

    scope = "envio_caso"
