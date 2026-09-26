from django.conf import settings
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


class TipoHecho(models.Model):
    """
    Catálogo de tipos de hecho victimizante (categorías reconocidas en
    Colombia: Ley 1448 de 2011 y actualizaciones). Editable desde el
    admin -no está fijo en código- por si hace falta ajustar la lista.
    """

    nombre = models.CharField(max_length=150, unique=True)
    orden = models.PositiveSmallIntegerField(default=0, help_text="Para ordenar en los selectores")
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Tipo de hecho"
        verbose_name_plural = "Tipos de hecho"

    def __str__(self):
        return self.nombre


def _ruta_soporte_caso(instance, filename):
    return f"casos/{instance.observatorio.codigo}/{filename}"


class CasoVictimizante(models.Model):
    """
    Registro de un hecho victimizante ocurrido en el municipio de un
    observatorio. A propósito NO guarda nombres ni datos que permitan
    identificar a víctimas individuales -solo cifras agregadas de
    población afectada-, y nace con 'requiere_reserva' en verdadero
    por defecto: el detalle de un caso NUNCA se expone en el tablero
    público, solo cifras agregadas (ver core/views_api.py).
    """

    class Zona(models.TextChoices):
        RURAL = "rural", "Rural"
        URBANA = "urbana", "Urbana"
        CENTRO_POBLADO = "centro_poblado", "Centro poblado"

    class PresuntoResponsable(models.TextChoices):
        GRUPO_ARMADO_ORGANIZADO = "grupo_armado_organizado", "Grupo armado organizado"
        AGENTE_ESTADO = "agente_estado", "Agente del Estado"
        GRUPO_NO_IDENTIFICADO = "grupo_no_identificado", "Grupo armado no identificado"
        NO_IDENTIFICADO = "no_identificado", "No identificado / desconocido"
        NO_APLICA = "no_aplica", "No aplica"

    class NivelVerificacion(models.TextChoices):
        CONFIRMADO = "confirmado", "Confirmado"
        EN_VERIFICACION = "en_verificacion", "En proceso de verificación"
        NO_VERIFICADO = "no_verificado", "No verificado"

    class EstadoSeguimiento(models.TextChoices):
        REPORTADO = "reportado", "Reportado"
        EN_GESTION = "en_gestion", "En gestión"
        REMITIDO = "remitido", "Remitido"
        CERRADO = "cerrado", "Cerrado"

    class EstadoRevision(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de revisión"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"

    # --- Identificación del caso ---
    observatorio = models.ForeignKey(Observatorio, on_delete=models.CASCADE, related_name="casos")
    fecha_hecho = models.DateField("Fecha en que ocurrió el hecho")
    vereda_corregimiento_barrio = models.CharField(max_length=200, blank=True)
    zona = models.CharField(max_length=20, choices=Zona.choices, blank=True)

    # --- Tipo de hecho ---
    tipo_hecho = models.ForeignKey(
        TipoHecho, on_delete=models.PROTECT, related_name="casos"
    )
    tipo_hecho_otro = models.CharField(
        "Especifique (si el tipo de hecho es 'Otro')", max_length=200, blank=True
    )

    # --- Presunto responsable ---
    presunto_responsable = models.CharField(
        max_length=30, choices=PresuntoResponsable.choices, blank=True
    )
    presunto_responsable_detalle = models.CharField(max_length=200, blank=True)

    # --- Población afectada (cifras agregadas, nunca nombres) ---
    num_personas_afectadas = models.PositiveIntegerField(null=True, blank=True)
    num_hombres = models.PositiveIntegerField(null=True, blank=True)
    num_mujeres = models.PositiveIntegerField(null=True, blank=True)
    num_otro_genero = models.PositiveIntegerField(null=True, blank=True)
    num_ninos_adolescentes = models.PositiveIntegerField(null=True, blank=True)
    num_adultos = models.PositiveIntegerField(null=True, blank=True)
    num_adultos_mayores = models.PositiveIntegerField(null=True, blank=True)
    num_familias_afectadas = models.PositiveIntegerField(null=True, blank=True)

    # --- Verificación y fuente ---
    fuente = models.CharField(max_length=200, blank=True)
    nivel_verificacion = models.CharField(
        max_length=20, choices=NivelVerificacion.choices,
        default=NivelVerificacion.NO_VERIFICADO,
    )
    archivo_soporte = models.FileField(
        upload_to=_ruta_soporte_caso, blank=True, null=True
    )

    # --- Descripción e impacto ---
    descripcion = models.TextField(
        "Descripción del hecho (sin datos que identifiquen víctimas)", blank=True
    )
    afectaciones_materiales = models.TextField(blank=True)
    necesidades_identificadas = models.TextField(blank=True)

    # --- Remisión y seguimiento ---
    remitido_a = models.CharField(max_length=200, blank=True)
    estado_seguimiento = models.CharField(
        max_length=20, choices=EstadoSeguimiento.choices, default=EstadoSeguimiento.REPORTADO
    )
    observaciones_seguimiento = models.TextField(blank=True)

    # --- Consentimiento y protección de datos ---
    autorizacion_registro = models.BooleanField(
        "¿Se autorizó expresamente registrar este hecho?", default=False
    )
    requiere_reserva = models.BooleanField(
        "¿Requiere manejo confidencial/reservado?", default=True
    )
    diligencia_nombre = models.CharField("Nombre de quien diligencia", max_length=200, blank=True)
    diligencia_rol = models.CharField("Rol de quien diligencia", max_length=150, blank=True)

    # --- Moderación (mismo patrón que el resto del proyecto) ---
    estado = models.CharField(
        max_length=12, choices=EstadoRevision.choices, default=EstadoRevision.PENDIENTE
    )
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="casos_revisados",
    )
    revisado_en = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.CharField(max_length=300, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_hecho"]
        verbose_name = "Caso victimizante"
        verbose_name_plural = "Casos victimizantes"

    def __str__(self):
        return f"{self.tipo_hecho} - {self.observatorio.codigo} ({self.fecha_hecho})"


class EnvioODK(models.Model):
    """
    Envío crudo recibido desde ODK Central (online u offline).
    Se guarda tal cual llega y luego se procesa hacia CasoVictimizante.
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
