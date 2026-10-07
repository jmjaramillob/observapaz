import django_filters

from .models import CasoVictimizante


class CasoVictimizanteFilter(django_filters.FilterSet):
    """
    Filtros de casos que usa el tablero (y /api/casos/ en general).

    - fecha_desde / fecha_hasta: periodo, sobre la fecha en que ocurrió
      el hecho (ambos extremos incluidos).
    - departamento / municipio: se resuelven por el observatorio del
      caso, que es donde hoy se guarda la ubicación.
    - observatorio, tipo_hecho, estado, fecha_hecho: igual que antes.
    """

    fecha_desde = django_filters.DateFilter(field_name="fecha_hecho", lookup_expr="gte")
    fecha_hasta = django_filters.DateFilter(field_name="fecha_hecho", lookup_expr="lte")
    departamento = django_filters.CharFilter(
        field_name="observatorio__departamento", lookup_expr="iexact"
    )
    municipio = django_filters.CharFilter(
        field_name="observatorio__municipio", lookup_expr="iexact"
    )

    class Meta:
        model = CasoVictimizante
        fields = ["observatorio", "tipo_hecho", "estado", "fecha_hecho"]
