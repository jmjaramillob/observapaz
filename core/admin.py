from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils import timezone

from .models import CasoVictimizante, EnvioODK, Observatorio, PerfilUsuario, TipoHecho


@admin.register(Observatorio)
class ObservatorioAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "departamento", "municipio", "activo")
    search_fields = ("codigo", "nombre", "departamento", "municipio")
    list_filter = ("activo", "departamento")


@admin.register(TipoHecho)
class TipoHechoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "activo")
    list_editable = ("orden", "activo")
    search_fields = ("nombre",)


@admin.register(CasoVictimizante)
class CasoVictimizanteAdmin(admin.ModelAdmin):
    list_display = (
        "tipo_hecho", "observatorio", "fecha_hecho", "num_personas_afectadas",
        "nivel_verificacion", "estado",
    )
    list_filter = ("estado", "tipo_hecho", "observatorio", "nivel_verificacion", "requiere_reserva")
    search_fields = ("descripcion", "vereda_corregimiento_barrio")
    date_hierarchy = "fecha_hecho"
    actions = ["aprobar_seleccionados", "rechazar_seleccionados"]

    @admin.action(description="Marcar seleccionados como aprobados")
    def aprobar_seleccionados(self, request, queryset):
        queryset.update(
            estado=CasoVictimizante.EstadoRevision.APROBADO,
            revisado_por=request.user,
            revisado_en=timezone.now(),
        )

    @admin.action(description="Marcar seleccionados como rechazados")
    def rechazar_seleccionados(self, request, queryset):
        queryset.update(
            estado=CasoVictimizante.EstadoRevision.RECHAZADO,
            revisado_por=request.user,
            revisado_en=timezone.now(),
        )


@admin.register(EnvioODK)
class EnvioODKAdmin(admin.ModelAdmin):
    list_display = ("formulario_id", "envio_id", "observatorio", "recibido_en", "procesado")
    list_filter = ("observatorio", "procesado")
    search_fields = ("formulario_id", "envio_id")


class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = "Observatorio asignado"


class UsuarioConPerfilAdmin(UserAdmin):
    """
    Reemplaza el admin de usuarios por defecto para poder asignar el
    observatorio de cada cuenta desde la misma pantalla de edición.
    Deja 'observatorio' vacío para las cuentas de coordinación, que
    ven el tablero completo de la Red.
    """

    inlines = (PerfilUsuarioInline,)
    list_display = ("username", "email", "observatorio_asignado", "is_staff", "is_active")

    def observatorio_asignado(self, obj):
        perfil = getattr(obj, "perfil", None)
        if perfil and perfil.observatorio:
            return perfil.observatorio.codigo
        return "Red / Coordinación"

    observatorio_asignado.short_description = "Observatorio"


admin.site.unregister(User)
admin.site.register(User, UsuarioConPerfilAdmin)
