from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from . import evidencias as reglas_evidencia
from .models import CasoVictimizante, EnvioODK, EvidenciaCaso, Observatorio, TipoHecho


class ObservatorioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Observatorio
        fields = "__all__"


class TipoHechoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoHecho
        fields = "__all__"


class EvidenciaCasoSerializer(serializers.ModelSerializer):
    """Datos de una foto/documento; el archivo se pide por 'url' (protegida)."""

    url = serializers.SerializerMethodField()
    es_foto = serializers.SerializerMethodField()
    se_ve_en_navegador = serializers.SerializerMethodField()

    class Meta:
        model = EvidenciaCaso
        fields = ["id", "nombre_original", "tipo", "tamano_bytes", "url", "es_foto", "se_ve_en_navegador"]

    def get_url(self, obj):
        return f"/api/casos/{obj.caso_id}/evidencias/{obj.id}/"

    def get_es_foto(self, obj):
        return reglas_evidencia.es_foto(obj.nombre_original)

    def get_se_ve_en_navegador(self, obj):
        return reglas_evidencia.se_ve_en_navegador(obj.nombre_original)


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

    evidencias = EvidenciaCasoSerializer(many=True, read_only=True)
    # Fotos y documentos que llegan junto con el caso (varios archivos con el
    # mismo nombre de campo 'archivos').
    archivos = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )

    class Meta:
        model = CasoVictimizante
        # 'archivo_soporte' queda solo como columna heredada: los archivos
        # nuevos se guardan como evidencias.
        exclude = ["archivo_soporte"]
        extra_kwargs = {
            campo: {"max_length": 2000}
            for campo in ("descripcion", "afectaciones_materiales", "necesidades_identificadas")
        }
        read_only_fields = [
            "estado", "revisado_por", "revisado_en", "motivo_rechazo", "creado_en", "actualizado_en",
        ]

    def validate_archivos(self, archivos):
        try:
            reglas_evidencia.validar_conjunto(archivos)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return archivos

    @transaction.atomic
    def create(self, validated_data):
        archivos = validated_data.pop("archivos", [])
        caso = self._crear_caso(validated_data)
        for a in archivos:
            EvidenciaCaso.objects.create(
                caso=caso,
                archivo=a,
                nombre_original=a.name[:255],
                tipo=(
                    EvidenciaCaso.Tipo.FOTO if reglas_evidencia.es_foto(a.name)
                    else EvidenciaCaso.Tipo.DOCUMENTO
                ),
                tamano_bytes=a.size,
            )
        return caso

    def _crear_caso(self, validated_data):
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
