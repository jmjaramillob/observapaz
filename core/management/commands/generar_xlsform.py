import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from openpyxl import Workbook

from core.models import Observatorio, TipoHecho


class Command(BaseCommand):
    help = (
        "Genera el XLSForm de reporte de casos para un observatorio, "
        "listo para subir a ODK Central (Proyecto → Formularios → Subir formulario)."
    )

    def add_arguments(self, parser):
        parser.add_argument("codigo", type=str, help="Código del observatorio, ej: OBS-007")
        parser.add_argument(
            "--salida",
            type=str,
            default=None,
            help="Carpeta donde guardar el archivo (por defecto: ./xlsforms/ dentro del proyecto)",
        )

    def handle(self, *args, **options):
        codigo = options["codigo"].upper()
        try:
            observatorio = Observatorio.objects.get(codigo__iexact=codigo)
        except Observatorio.DoesNotExist:
            raise CommandError(f"No existe ningún observatorio con código '{codigo}'.")

        tipos_hecho = TipoHecho.objects.filter(activo=True).order_by("orden", "nombre")
        if not tipos_hecho.exists():
            self.stdout.write(
                self.style.WARNING(
                    "Todavía no hay ningún tipo de hecho activo en el catálogo. El "
                    "formulario se genera igual, pero el desplegable saldrá vacío."
                )
            )

        wb = Workbook()

        survey = wb.active
        survey.title = "survey"
        survey.append(["type", "name", "label", "required", "appearance", "relevant", "hint"])
        survey.append(["start", "start", "", "", "", "", ""])
        survey.append(["end", "end", "", "", "", "", ""])
        survey.append(["date", "fecha_hecho", "Fecha en que ocurrió el hecho", "yes", "", "", ""])
        survey.append(["text", "vereda_corregimiento_barrio", "Vereda, corregimiento o barrio", "no", "", "", ""])
        survey.append(["select_one zonas", "zona", "Zona", "no", "", "", ""])
        survey.append(["select_one tipos_hecho", "tipo_hecho", "Tipo de hecho", "yes", "", "", ""])
        survey.append(
            ["text", "tipo_hecho_otro", "Especifique el tipo de hecho", "no", "", "${tipo_hecho}='otro'", ""]
        )
        survey.append(["select_one responsables", "presunto_responsable", "Presunto responsable", "no", "", "", ""])
        survey.append(["text", "presunto_responsable_detalle", "Detalle del presunto responsable", "no", "", "", ""])
        survey.append(["integer", "num_personas_afectadas", "Número total de personas afectadas", "no", "", "", ""])
        survey.append(["integer", "num_hombres", "Número de hombres afectados", "no", "", "", ""])
        survey.append(["integer", "num_mujeres", "Número de mujeres afectadas", "no", "", "", ""])
        survey.append(["integer", "num_otro_genero", "Número de personas de otro género afectadas", "no", "", "", ""])
        survey.append(["integer", "num_ninos_adolescentes", "Número de niños, niñas y adolescentes afectados", "no", "", "", ""])
        survey.append(["integer", "num_adultos", "Número de adultos afectados", "no", "", "", ""])
        survey.append(["integer", "num_adultos_mayores", "Número de adultos mayores afectados", "no", "", "", ""])
        survey.append(["integer", "num_familias_afectadas", "Número de familias afectadas", "no", "", "", ""])
        survey.append(["text", "fuente", "Fuente de la información", "no", "", "", ""])
        survey.append(["select_one verificacion", "nivel_verificacion", "Nivel de verificación", "no", "", "", ""])
        survey.append(
            ["text", "descripcion", "Descripción del hecho", "no", "multiline", "",
             "No incluya nombres ni datos que identifiquen a víctimas."]
        )
        survey.append(["text", "afectaciones_materiales", "Afectaciones materiales", "no", "multiline", "", ""])
        survey.append(["text", "necesidades_identificadas", "Necesidades inmediatas identificadas", "no", "multiline", "", ""])
        survey.append(["select_one si_no", "autorizacion_registro", "¿Se autorizó expresamente registrar este hecho?", "yes", "", "", ""])
        survey.append(["select_one si_no", "requiere_reserva", "¿Requiere manejo confidencial/reservado?", "no", "", "", ""])
        survey.append(["text", "diligencia_nombre", "Nombre de quien diligencia", "no", "", "", ""])
        survey.append(["text", "diligencia_rol", "Rol de quien diligencia", "no", "", "", ""])

        choices = wb.create_sheet("choices")
        choices.append(["list_name", "name", "label"])
        for valor, etiqueta in [
            ("rural", "Rural"), ("urbana", "Urbana"), ("centro_poblado", "Centro poblado"),
        ]:
            choices.append(["zonas", valor, etiqueta])
        for tipo in tipos_hecho:
            # El 'name' es el ID del TipoHecho en nuestra base -así, al
            # sincronizar, el envío ya trae la referencia exacta, sin
            # tener que adivinar por nombre-. "Otro" queda igual pero
            # además habilita el campo de texto libre de arriba.
            choices.append(["tipos_hecho", str(tipo.id), tipo.nombre])
        for valor, etiqueta in [
            ("grupo_armado_organizado", "Grupo armado organizado"),
            ("agente_estado", "Agente del Estado"),
            ("grupo_no_identificado", "Grupo armado no identificado"),
            ("no_identificado", "No identificado / desconocido"),
            ("no_aplica", "No aplica"),
        ]:
            choices.append(["responsables", valor, etiqueta])
        for valor, etiqueta in [
            ("confirmado", "Confirmado"),
            ("en_verificacion", "En proceso de verificación"),
            ("no_verificado", "No verificado"),
        ]:
            choices.append(["verificacion", valor, etiqueta])
        for valor, etiqueta in [("si", "Sí"), ("no", "No")]:
            choices.append(["si_no", valor, etiqueta])

        settings_sheet = wb.create_sheet("settings")
        settings_sheet.append(["form_title", "form_id", "version", "default_language"])
        version = datetime.datetime.now().strftime("%Y%m%d%H%M")
        form_id = f"observapaz_caso_{codigo.lower().replace('-', '_')}"
        settings_sheet.append([f"OBSERVAPAZ - Reporte de casos - {codigo}", form_id, version, "es"])

        carpeta = Path(options["salida"] or (Path(settings.BASE_DIR) / "xlsforms"))
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / f"{codigo}.xlsx"
        wb.save(ruta)

        self.stdout.write(
            self.style.SUCCESS(
                f"Listo: {ruta} ({tipos_hecho.count()} tipo(s) de hecho).\n"
                f"form_id: {form_id}  |  versión: {version}\n"
                "Súbelo en ODK Central: Proyecto → Formularios → Subir formulario. "
                "Si ya existe, subir de nuevo con la nueva versión lo actualiza."
            )
        )
