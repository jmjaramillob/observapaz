from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class Observatorio(models.Model):
    """
    Cada uno de los 24 espacios funcionales (OBS-001 a OBS-024).
    Ya no son tenants/esquemas separados, sino un registro más
    dentro de la base de datos única.
    """

    codigo = models.CharField(max_length=10, unique=True, help_text="Ej: OBS-001")
    nombre = models.CharField(max_length=200)
    departamento = models.CharField(max_length=120, blank=True)
    municipio = models.CharField(max_length=120, blank=True)
    coordinador = models.CharField(max_length=150, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "Observatorio"
        verbose_name_plural = "Observatorios"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class CategoriaIndicador(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Categoría de indicador"
        verbose_name_plural = "Categorías de indicadores"

    def __str__(self):
        return self.nombre


class Indicador(models.Model):
    observatorio = models.ForeignKey(
        Observatorio, on_delete=models.CASCADE, related_name="indicadores"
    )
    categoria = models.ForeignKey(
        CategoriaIndicador, on_delete=models.SET_NULL, null=True, related_name="indicadores"
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    unidad = models.CharField(max_length=50, blank=True, help_text="Ej: casos, %, personas")
    meta = models.FloatField(null=True, blank=True, help_text="Valor de referencia u objetivo")
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["observatorio", "nombre"]
        verbose_name = "Indicador"
        verbose_name_plural = "Indicadores"

    def __str__(self):
        return f"{self.nombre} ({self.observatorio.codigo})"


class RegistroIndicador(models.Model):
    """Un valor puntual de un indicador en una fecha determinada."""

    class EstadoRegistro(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de revisión"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"

    indicador = models.ForeignKey(
        Indicador, on_delete=models.CASCADE, related_name="registros"
    )
    fecha = models.DateField()
    valor = models.FloatField()
    fuente = models.CharField(max_length=200, blank=True)
    observaciones = models.TextField(blank=True)
    ubicacion = gis_models.PointField(
        null=True, blank=True, srid=4326, help_text="Coordenada geográfica del registro"
    )
    estado = models.CharField(
        max_length=12, choices=EstadoRegistro.choices, default=EstadoRegistro.PENDIENTE
    )
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_revisados",
    )
    revisado_en = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.CharField(max_length=300, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Registro de indicador"
        verbose_name_plural = "Registros de indicadores"

    def __str__(self):
        return f"{self.indicador} - {self.fecha}: {self.valor}"


class EnvioODK(models.Model):
    """
    Envío crudo recibido desde ODK Central (online u offline).
    Se guarda tal cual llega y luego se procesa hacia RegistroIndicador.
    """

    observatorio = models.ForeignKey(
        Observatorio, on_delete=models.CASCADE, related_name="envios_odk"
    )
    formulario_id = models.CharField(max_length=150)
    envio_id = models.CharField(max_length=150, unique=True)
    datos = models.JSONField()
    recibido_en = models.DateTimeField(auto_now_add=True)
    procesado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-recibido_en"]
        verbose_name = "Envío ODK"
        verbose_name_plural = "Envíos ODK"

    def __str__(self):
        return f"{self.formulario_id} ({self.envio_id})"


class PerfilUsuario(models.Model):
    """
    Liga una cuenta de usuario con el observatorio al que pertenece.

    - Si 'observatorio' tiene un valor: el usuario solo puede ver el
      tablero privado de ESE observatorio (uso pensado para las 24
      cuentas de los observatorios).
    - Si 'observatorio' está vacío: el usuario ve el tablero completo
      de toda la Red (uso pensado para el equipo de coordinación).
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    observatorio = models.ForeignKey(
        Observatorio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usuarios",
        help_text="Vacío = usuario de coordinación, ve toda la Red.",
    )

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self):
        destino = self.observatorio.codigo if self.observatorio else "Red / Coordinación"
        return f"{self.usuario.username} ({destino})"
