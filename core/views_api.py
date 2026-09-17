from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from .models import CategoriaIndicador, EnvioODK, Indicador, Observatorio, RegistroIndicador
from .serializers import (
    CategoriaIndicadorSerializer,
    EnvioODKSerializer,
    IndicadorSerializer,
    ObservatorioSerializer,
    RegistroIndicadorSerializer,
)


class ObservatorioViewSet(viewsets.ModelViewSet):
    queryset = Observatorio.objects.all()
    serializer_class = ObservatorioSerializer
    filterset_fields = ["activo", "departamento"]
    search_fields = ["codigo", "nombre"]


class CategoriaIndicadorViewSet(viewsets.ModelViewSet):
    queryset = CategoriaIndicador.objects.all()
    serializer_class = CategoriaIndicadorSerializer


class IndicadorViewSet(viewsets.ModelViewSet):
    queryset = Indicador.objects.select_related("observatorio", "categoria").all()
    serializer_class = IndicadorSerializer
    filterset_fields = ["observatorio", "categoria", "activo"]


class RegistroIndicadorViewSet(viewsets.ModelViewSet):
    queryset = RegistroIndicador.objects.select_related("indicador").all()
    serializer_class = RegistroIndicadorSerializer
    filterset_fields = ["indicador", "fecha"]


class EnvioODKViewSet(viewsets.ModelViewSet):
    """
    Endpoint donde ODK Central (vía webhook o tarea programada) deposita
    los envíos crudos para su posterior procesamiento hacia RegistroIndicador.
    """

    queryset = EnvioODK.objects.select_related("observatorio").all()
    serializer_class = EnvioODKSerializer
    filterset_fields = ["observatorio", "procesado", "formulario_id"]
