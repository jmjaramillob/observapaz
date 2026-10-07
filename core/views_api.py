from django.db.models import Count, Max, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import CasoVictimizanteFilter
from .models import CasoVictimizante, EnvioODK, Observatorio, TipoHecho
from .permissions import CasoVictimizantePermiso, SoloAutenticadoPermiso, SoloLecturaPublicaPermiso
from .reportes import generar_pdf_caso
from .serializers import (
    CasoVictimizanteSerializer,
    EnvioODKSerializer,
    ObservatorioSerializer,
    TipoHechoSerializer,
)
from .throttling import EnvioCasoThrottle
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
    filterset_class = CasoVictimizanteFilter

    def get_throttles(self):
        """
        El límite de envíos (EnvioCasoThrottle) solo aplica al crear un
        caso sin sesión iniciada -el formulario público-. El resto de
        acciones (listar, resumen, pendientes, aprobar, rechazar, o
        crear ya logueado) sigue sin ningún límite adicional.
        """
        if self.action == "create" and not self.request.user.is_authenticated:
            return [EnvioCasoThrottle()]
        return super().get_throttles()

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

        # "Observatorios" del tablero: los activos que caen dentro del
        # alcance territorial elegido (observatorio, departamento,
        # municipio) y, si el usuario es de un observatorio, solo el suyo.
        # El periodo y el tipo de hecho no cambian cuántos observatorios hay.
        params = request.query_params
        obs_usuario = observatorio_del_usuario(request.user)
        observatorios = Observatorio.objects.filter(activo=True)
        if obs_usuario:
            observatorios = observatorios.filter(pk=obs_usuario.pk)
        if params.get("observatorio"):
            observatorios = observatorios.filter(pk=params["observatorio"])
        if params.get("departamento"):
            observatorios = observatorios.filter(departamento__iexact=params["departamento"])
        if params.get("municipio"):
            observatorios = observatorios.filter(municipio__iexact=params["municipio"])

        por_municipio = (
            qs.values("observatorio__departamento", "observatorio__municipio")
            .annotate(total=Count("id"))
            .order_by("-total", "observatorio__municipio")
        )
        nombres_municipio = [r["observatorio__municipio"] or "Sin municipio" for r in por_municipio]
        repetidos = {n for n in nombres_municipio if nombres_municipio.count(n) > 1}
        etiquetas_municipio = [
            f'{nombre} ({r["observatorio__departamento"] or "sin departamento"})'
            if nombre in repetidos else nombre
            for nombre, r in zip(nombres_municipio, por_municipio)
        ]

        por_tipo = (
            qs.values("tipo_hecho__nombre")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        por_observatorio = (
            qs.values("observatorio__codigo", "observatorio__nombre")
            .annotate(total=Count("id"))
            .order_by("-total", "observatorio__codigo")
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

        # Cobertura territorial de los casos filtrados y fecha del último
        # cambio en ellos (para los indicadores "Municipios con reportes"
        # y "Última actualización").
        municipios_con_reportes = sum(1 for r in por_municipio if r["observatorio__municipio"])
        departamentos_con_reportes = len(
            {r["observatorio__departamento"] for r in por_municipio if r["observatorio__departamento"]}
        )
        ultimo_cambio = qs.aggregate(m=Max("actualizado_en"))["m"]

        return Response(
            {
                "total_observatorios": observatorios.count(),
                "municipios_con_reportes": municipios_con_reportes,
                "departamentos_con_reportes": departamentos_con_reportes,
                "ultima_actualizacion": (
                    timezone.localtime(ultimo_cambio).date().isoformat() if ultimo_cambio else None
                ),
                "total_casos": qs.count(),
                "poblacion": {k: (v or 0) for k, v in poblacion.items()},
                "por_tipo_hecho": {
                    "labels": [r["tipo_hecho__nombre"] for r in por_tipo],
                    "data": [r["total"] for r in por_tipo],
                },
                "por_municipio": {
                    "labels": etiquetas_municipio,
                    "data": [r["total"] for r in por_municipio],
                },
                "por_observatorio": {
                    "labels": [r["observatorio__codigo"] for r in por_observatorio],
                    "nombres": [r["observatorio__nombre"] for r in por_observatorio],
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

    @action(detail=True, methods=["get"])
    def reporte(self, request, pk=None):
        """
        Reporte PDF de este caso, con el mismo encabezado institucional
        del sitio y todos los campos de la página de detalle. Requiere
        sesión iniciada -self.get_object() ya respeta el aislamiento por
        observatorio de get_queryset(), así que un gestor no puede
        descargar el reporte de un caso ajeno-.
        """
        caso = self.get_object()
        pdf = generar_pdf_caso(caso)
        nombre_archivo = f"reporte_caso_{caso.id}.pdf"
        respuesta = HttpResponse(pdf, content_type="application/pdf")
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
        return respuesta

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
