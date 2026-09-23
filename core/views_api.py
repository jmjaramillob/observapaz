from django.db.models import Avg, Count, Max
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import CategoriaIndicador, EnvioODK, Indicador, Observatorio, RegistroIndicador
from .permissions import RegistroIndicadorPermiso, SoloAutenticadoPermiso, SoloLecturaPublicaPermiso
from .serializers import (
    CategoriaIndicadorSerializer,
    EnvioODKSerializer,
    IndicadorSerializer,
    ObservatorioSerializer,
    RegistroIndicadorSerializer,
)
from .utils import observatorio_del_usuario


class ObservatorioViewSet(viewsets.ModelViewSet):
    queryset = Observatorio.objects.all()
    serializer_class = ObservatorioSerializer
    permission_classes = [SoloLecturaPublicaPermiso]
    filterset_fields = ["activo", "departamento"]
    search_fields = ["codigo", "nombre"]


class CategoriaIndicadorViewSet(viewsets.ModelViewSet):
    queryset = CategoriaIndicador.objects.all()
    serializer_class = CategoriaIndicadorSerializer
    permission_classes = [SoloLecturaPublicaPermiso]


class IndicadorViewSet(viewsets.ModelViewSet):
    queryset = Indicador.objects.select_related("observatorio", "categoria").all()
    serializer_class = IndicadorSerializer
    permission_classes = [SoloLecturaPublicaPermiso]
    filterset_fields = ["observatorio", "categoria", "activo"]

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        """
        Lista de indicadores con su último valor, promedio y total de
        registros ya calculados -para no tener que traer cada registro
        individual solo para armar la tabla del tablero-.
        Acepta los mismos filtros que el listado normal, ej.
        /api/indicadores/resumen/?observatorio=7
        """
        qs = (
            self.filter_queryset(self.get_queryset())
            .filter(activo=True)
            .annotate(
                ultimo_valor=Max("registros__valor"),
                promedio=Avg("registros__valor"),
                total_registros=Count("registros"),
            )
            .order_by("observatorio__codigo", "nombre")
        )
        datos = [
            {
                "id": i.id,
                "nombre": i.nombre,
                "unidad": i.unidad,
                "meta": i.meta,
                "observatorio_codigo": i.observatorio.codigo,
                "categoria_nombre": i.categoria.nombre if i.categoria else None,
                "ultimo_valor": i.ultimo_valor,
                "promedio": round(i.promedio, 1) if i.promedio is not None else None,
                "total_registros": i.total_registros,
            }
            for i in qs
        ]
        return Response(datos)


class RegistroIndicadorViewSet(viewsets.ModelViewSet):
    serializer_class = RegistroIndicadorSerializer
    permission_classes = [RegistroIndicadorPermiso]
    filterset_fields = ["indicador", "indicador__observatorio", "fecha"]

    def get_queryset(self):
        """
        Punto clave del aislamiento: si el usuario que consulta está
        ligado a un observatorio, SOLO ve sus propios registros -sin
        importar qué filtros le pase en la URL-. Si es de coordinación
        (o anónimo, para el caso de 'resumen'), no se acota aquí.
        """
        qs = RegistroIndicador.objects.select_related(
            "indicador", "indicador__observatorio", "indicador__categoria"
        )
        obs = observatorio_del_usuario(self.request.user)
        if obs:
            qs = qs.filter(indicador__observatorio=obs)
        return qs

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        """
        Cifras agregadas para los gráficos (registros por observatorio,
        por categoría y por mes) y los totales de las tarjetas. Solo
        cuenta registros APROBADOS -los pendientes de revisión no
        entran a las cifras oficiales hasta que el gestor los valide-,
        y nunca expone fuente/observaciones/ubicación de cada uno.
        """
        qs = self.filter_queryset(self.get_queryset()).filter(
            estado=RegistroIndicador.EstadoRegistro.APROBADO
        )

        obs_usuario = observatorio_del_usuario(request.user)
        observatorio_param = request.query_params.get("indicador__observatorio")
        alcance_unico = bool(obs_usuario or observatorio_param)

        por_observatorio = (
            qs.values("indicador__observatorio__codigo")
            .annotate(total=Count("id"))
            .order_by("indicador__observatorio__codigo")
        )
        por_categoria = (
            qs.exclude(indicador__categoria__isnull=True)
            .values("indicador__categoria__nombre")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        por_mes = (
            qs.annotate(mes=TruncMonth("fecha"))
            .values("mes")
            .annotate(total=Count("id"))
            .order_by("mes")
        )

        indicadores_qs = Indicador.objects.filter(activo=True)
        if obs_usuario:
            indicadores_qs = indicadores_qs.filter(observatorio=obs_usuario)
        elif observatorio_param:
            indicadores_qs = indicadores_qs.filter(observatorio_id=observatorio_param)

        return Response(
            {
                "total_observatorios": (
                    1 if alcance_unico else Observatorio.objects.filter(activo=True).count()
                ),
                "total_indicadores": indicadores_qs.count(),
                "total_registros": qs.count(),
                "por_observatorio": {
                    "labels": [r["indicador__observatorio__codigo"] for r in por_observatorio],
                    "data": [r["total"] for r in por_observatorio],
                },
                "por_categoria": {
                    "labels": [r["indicador__categoria__nombre"] for r in por_categoria],
                    "data": [r["total"] for r in por_categoria],
                },
                "por_mes": {
                    "labels": [r["mes"].strftime("%Y-%m") for r in por_mes if r["mes"]],
                    "data": [r["total"] for r in por_mes if r["mes"]],
                },
            }
        )

    @action(detail=False, methods=["get"])
    def pendientes(self, request):
        """
        Registros pendientes de revisión, dentro del alcance del
        usuario (su propio observatorio, o toda la Red si es de
        coordinación). Requiere sesión iniciada -lo aplica el permiso-.
        """
        qs = self.get_queryset().filter(
            estado=RegistroIndicador.EstadoRegistro.PENDIENTE
        ).order_by("-creado_en")
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        """
        Marca un registro como válido. self.get_object() ya respeta el
        alcance de get_queryset(): un gestor no puede aprobar registros
        de otro observatorio -le daría 404, ni siquiera 403-.
        """
        registro = self.get_object()
        registro.estado = RegistroIndicador.EstadoRegistro.APROBADO
        registro.revisado_por = request.user
        registro.revisado_en = timezone.now()
        registro.motivo_rechazo = ""
        registro.save()
        return Response(self.get_serializer(registro).data)

    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        """Marca un registro como no válido, con un motivo opcional."""
        registro = self.get_object()
        registro.estado = RegistroIndicador.EstadoRegistro.RECHAZADO
        registro.revisado_por = request.user
        registro.revisado_en = timezone.now()
        registro.motivo_rechazo = request.data.get("motivo", "")
        registro.save()
        return Response(self.get_serializer(registro).data)


class EnvioODKViewSet(viewsets.ModelViewSet):
    """
    Endpoint donde ODK Central (vía webhook o tarea programada) deposita
    los envíos crudos para su posterior procesamiento hacia
    RegistroIndicador. Requiere sesión iniciada y respeta el mismo
    aislamiento por observatorio que los registros.
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
