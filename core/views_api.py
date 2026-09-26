from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import CasoVictimizante, EnvioODK, Observatorio, TipoHecho
from .permissions import CasoVictimizantePermiso, SoloAutenticadoPermiso, SoloLecturaPublicaPermiso
from .serializers import (
    CasoVictimizanteSerializer,
    EnvioODKSerializer,
    ObservatorioSerializer,
    TipoHechoSerializer,
)
from .utils import observatorio_del_usuario


class ObservatorioViewSet(viewsets.ModelViewSet):
    queryset = Observatorio.objects.all()
    serializer_class = ObservatorioSerializer
    permission_classes = [SoloLecturaPublicaPermiso]
    filterset_fields = ["activo", "departamento"]
    search_fields = ["codigo", "nombre"]


class TipoHechoViewSet(viewsets.ModelViewSet):
    queryset = TipoHecho.objects.all()
    serializer_class = TipoHechoSerializer
    permission_classes = [SoloLecturaPublicaPermiso]
    filterset_fields = ["activo"]


class CasoVictimizanteViewSet(viewsets.ModelViewSet):
    serializer_class = CasoVictimizanteSerializer
    permission_classes = [CasoVictimizantePermiso]
    filterset_fields = ["observatorio", "tipo_hecho", "estado", "fecha_hecho"]

    def get_queryset(self):
        """
        Punto clave del aislamiento: si el usuario que consulta está
        ligado a un observatorio, SOLO ve sus propios casos -sin
        importar qué filtros le pase en la URL-. Si es de coordinación
        (o anónimo, para el caso de 'resumen'), no se acota aquí.
        """
        qs = CasoVictimizante.objects.select_related("observatorio", "tipo_hecho")
        obs = observatorio_del_usuario(self.request.user)
        if obs:
            qs = qs.filter(observatorio=obs)
        return qs

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        """
        Cifras agregadas para el tablero (totales, por tipo de hecho,
        por observatorio, por mes). Solo cuenta casos APROBADOS -los
        pendientes de revisión no entran a las cifras oficiales hasta
        que el gestor los valide-, y NUNCA expone el detalle de un
        caso individual (descripción, fuente, ubicación exacta): eso
        solo se ve listando /api/casos/ con sesión iniciada.
        """
        qs = self.filter_queryset(self.get_queryset()).filter(
            estado=CasoVictimizante.EstadoRevision.APROBADO
        )

        obs_usuario = observatorio_del_usuario(request.user)
        observatorio_param = request.query_params.get("observatorio")
        alcance_unico = bool(obs_usuario or observatorio_param)

        por_tipo = (
            qs.values("tipo_hecho__nombre")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        por_observatorio = (
            qs.values("observatorio__codigo")
            .annotate(total=Count("id"))
            .order_by("observatorio__codigo")
        )
        por_mes = (
            qs.annotate(mes=TruncMonth("fecha_hecho"))
            .values("mes")
            .annotate(total=Count("id"))
            .order_by("mes")
        )
        poblacion = qs.aggregate(
            personas=Sum("num_personas_afectadas"),
            hombres=Sum("num_hombres"),
            mujeres=Sum("num_mujeres"),
            ninos_adolescentes=Sum("num_ninos_adolescentes"),
            adultos_mayores=Sum("num_adultos_mayores"),
            familias=Sum("num_familias_afectadas"),
        )

        return Response(
            {
                "total_observatorios": (
                    1 if alcance_unico else Observatorio.objects.filter(activo=True).count()
                ),
                "total_casos": qs.count(),
                "poblacion": {k: (v or 0) for k, v in poblacion.items()},
                "por_tipo_hecho": {
                    "labels": [r["tipo_hecho__nombre"] for r in por_tipo],
                    "data": [r["total"] for r in por_tipo],
                },
                "por_observatorio": {
                    "labels": [r["observatorio__codigo"] for r in por_observatorio],
                    "data": [r["total"] for r in por_observatorio],
                },
                "por_mes": {
                    "labels": [r["mes"].strftime("%Y-%m") for r in por_mes if r["mes"]],
                    "data": [r["total"] for r in por_mes if r["mes"]],
                },
            }
        )

    @action(detail=False, methods=["get"])
    def pendientes(self, request):
        """Casos pendientes de revisión, dentro del alcance del usuario."""
        qs = self.get_queryset().filter(
            estado=CasoVictimizante.EstadoRevision.PENDIENTE
        ).order_by("-creado_en")
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        """
        Marca un caso como válido. self.get_object() ya respeta el
        alcance de get_queryset(): un gestor no puede aprobar casos de
        otro observatorio -le daría 404, ni siquiera 403-.
        """
        caso = self.get_object()
        caso.estado = CasoVictimizante.EstadoRevision.APROBADO
        caso.revisado_por = request.user
        caso.revisado_en = timezone.now()
        caso.motivo_rechazo = ""
        caso.save()
        return Response(self.get_serializer(caso).data)

    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        """Marca un caso como no válido, con un motivo opcional."""
        caso = self.get_object()
        caso.estado = CasoVictimizante.EstadoRevision.RECHAZADO
        caso.revisado_por = request.user
        caso.revisado_en = timezone.now()
        caso.motivo_rechazo = request.data.get("motivo", "")
        caso.save()
        return Response(self.get_serializer(caso).data)


class EnvioODKViewSet(viewsets.ModelViewSet):
    """
    Endpoint donde ODK Central (vía webhook o tarea programada) deposita
    los envíos crudos para su posterior procesamiento hacia
    CasoVictimizante. Requiere sesión iniciada y respeta el mismo
    aislamiento por observatorio que los casos.
    """

    serializer_class = EnvioODKSerializer
    permission_classes = [SoloAutenticadoPermiso]
    filterset_fields = ["observatorio", "procesado", "formulario_id"]

    def get_queryset(self):
        qs = EnvioODK.objects.select_related("observatorio")
        obs = observatorio_del_usuario(self.request.user)
        if obs:
            qs = qs.filter(observatorio=obs)
        return qs
