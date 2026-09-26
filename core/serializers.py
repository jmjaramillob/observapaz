from django.utils import timezone
from rest_framework import serializers

from .models import CasoVictimizante, EnvioODK, Observatorio, TipoHecho


class ObservatorioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Observatorio
        fields = "__all__"


class TipoHechoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoHecho
        fields = "__all__"


class CasoVictimizanteSerializer(serializers.ModelSerializer):
    """
    'estado' es de solo lectura: quien envía el caso nunca decide si
    queda aprobado -eso lo controla el servidor en create(), o el
    gestor desde las acciones aprobar/rechazar del ViewSet-.
    """

    observatorio_codigo = serializers.CharField(source="observatorio.codigo", read_only=True)
    tipo_hecho_nombre = serializers.CharField(source="tipo_hecho.nombre", read_only=True)
    revisado_por_nombre = serializers.CharField(
        source="revisado_por.username", read_only=True, default=None
    )
    estado = serializers.ChoiceField(
        choices=CasoVictimizante.EstadoRevision.choices, read_only=True
    )

    class Meta:
        model = CasoVictimizante
        fields = "__all__"
        read_only_fields = [
            "estado", "revisado_por", "revisado_en", "motivo_rechazo", "creado_en", "actualizado_en",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["estado"] = CasoVictimizante.EstadoRevision.APROBADO
            validated_data["revisado_por"] = request.user
            validated_data["revisado_en"] = timezone.now()
        return super().create(validated_data)


class EnvioODKSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvioODK
        fields = "__all__"
        read_only_fields = ("recibido_en", "procesado")
