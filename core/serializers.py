from django.contrib.gis.geos import Point
from django.utils import timezone
from rest_framework import serializers

from .models import CategoriaIndicador, EnvioODK, Indicador, Observatorio, RegistroIndicador


class ObservatorioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Observatorio
        fields = "__all__"


class CategoriaIndicadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaIndicador
        fields = "__all__"


class IndicadorSerializer(serializers.ModelSerializer):
    observatorio_codigo = serializers.CharField(source="observatorio.codigo", read_only=True)

    class Meta:
        model = Indicador
        fields = "__all__"


class RegistroIndicadorSerializer(serializers.ModelSerializer):
    """
    Notas:
    - 'ubicacion' es un campo geográfico (PostGIS); se recibe como
      'latitud'/'longitud' y se arma el punto al guardar.
    - 'estado' es de solo lectura a propósito: quien envía el registro
      NUNCA puede decidir si queda aprobado -eso lo controla el
      servidor en create(), o el gestor desde las acciones
      aprobar/rechazar del ViewSet-.
    """

    indicador_nombre = serializers.CharField(source="indicador.nombre", read_only=True)
    observatorio_codigo = serializers.CharField(
        source="indicador.observatorio.codigo", read_only=True
    )
    latitud = serializers.FloatField(write_only=True, required=False, allow_null=True)
    longitud = serializers.FloatField(write_only=True, required=False, allow_null=True)
    estado = serializers.ChoiceField(
        choices=RegistroIndicador.EstadoRegistro.choices, read_only=True
    )
    revisado_por_nombre = serializers.CharField(
        source="revisado_por.username", read_only=True, default=None
    )

    class Meta:
        model = RegistroIndicador
        fields = [
            "id",
            "indicador",
            "indicador_nombre",
            "observatorio_codigo",
            "fecha",
            "valor",
            "fuente",
            "observaciones",
            "latitud",
            "longitud",
            "estado",
            "revisado_por_nombre",
            "revisado_en",
            "motivo_rechazo",
            "creado_en",
        ]
        read_only_fields = ["creado_en", "revisado_en", "motivo_rechazo"]

    def create(self, validated_data):
        lat = validated_data.pop("latitud", None)
        lon = validated_data.pop("longitud", None)
        if lat is not None and lon is not None:
            validated_data["ubicacion"] = Point(lon, lat, srid=4326)

        # Un registro creado por alguien YA autenticado (el propio
        # equipo del observatorio con su usuario) se aprueba solo, sin
        # pasar por moderación: quien lo escribió ya inició sesión.
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["estado"] = RegistroIndicador.EstadoRegistro.APROBADO
            validated_data["revisado_por"] = request.user
            validated_data["revisado_en"] = timezone.now()

        return super().create(validated_data)


class EnvioODKSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvioODK
        fields = "__all__"
        read_only_fields = ("recibido_en", "procesado")
