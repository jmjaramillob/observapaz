from django.contrib import admin

from .models import CategoriaIndicador, EnvioODK, Indicador, Observatorio, RegistroIndicador


@admin.register(Observatorio)
class ObservatorioAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "departamento", "municipio", "activo")
    search_fields = ("codigo", "nombre", "departamento", "municipio")
    list_filter = ("activo", "departamento")


@admin.register(CategoriaIndicador)
class CategoriaIndicadorAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(Indicador)
class IndicadorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "observatorio", "categoria", "unidad", "meta", "activo")
    list_filter = ("observatorio", "categoria", "activo")
    search_fields = ("nombre",)


@admin.register(RegistroIndicador)
class RegistroIndicadorAdmin(admin.ModelAdmin):
    list_display = ("indicador", "fecha", "valor", "fuente")
    list_filter = ("indicador__observatorio", "fecha")
    date_hierarchy = "fecha"


@admin.register(EnvioODK)
class EnvioODKAdmin(admin.ModelAdmin):
    list_display = ("formulario_id", "envio_id", "observatorio", "recibido_en", "procesado")
    list_filter = ("observatorio", "procesado")
    search_fields = ("formulario_id", "envio_id")
