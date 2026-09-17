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
    indicador_nombre = serializers.CharField(source="indicador.nombre", read_only=True)

    class Meta:
        model = RegistroIndicador
        fields = "__all__"


class EnvioODKSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvioODK
        fields = "__all__"
        read_only_fields = ("recibido_en", "procesado")
