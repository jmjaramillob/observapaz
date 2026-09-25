import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from openpyxl import Workbook

from core.models import Indicador, Observatorio


class Command(BaseCommand):
    help = (
        "Genera un XLSForm con los indicadores activos de un observatorio, "
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

        indicadores = Indicador.objects.filter(observatorio=observatorio, activo=True).order_by("nombre")
        if not indicadores.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"{codigo} todavía no tiene indicadores activos. El formulario se genera "
                    "igual, pero el desplegable de indicadores saldrá vacío hasta que agregues alguno."
                )
            )

        wb = Workbook()

        survey = wb.active
        survey.title = "survey"
        survey.append(["type", "name", "label", "required", "appearance"])
        survey.append(["start", "start", "", "", ""])
        survey.append(["end", "end", "", "", ""])
        survey.append(["select_one indicadores", "indicador", "Indicador", "yes", ""])
        survey.append(["date", "fecha", "Fecha del dato", "yes", ""])
        survey.append(["decimal", "valor", "Valor registrado", "yes", ""])
        survey.append(["text", "fuente", "Fuente de la información", "no", ""])
        survey.append(["text", "observaciones", "Observaciones", "no", "multiline"])
        survey.append(["geopoint", "ubicacion", "Ubicación (opcional)", "no", ""])

        choices = wb.create_sheet("choices")
        choices.append(["list_name", "name", "label"])
        for ind in indicadores:
            # El 'name' de cada opción es el ID del indicador en nuestra
            # base -así, al sincronizar, el envío ya trae la referencia
            # exacta al Indicador, sin tener que adivinar por nombre-.
            choices.append(["indicadores", str(ind.id), ind.nombre])

        settings_sheet = wb.create_sheet("settings")
        settings_sheet.append(["form_title", "form_id", "version", "default_language"])
        version = datetime.datetime.now().strftime("%Y%m%d%H%M")
        form_id = f"observapaz_{codigo.lower().replace('-', '_')}"
        settings_sheet.append([f"OBSERVAPAZ - {codigo}", form_id, version, "es"])

        carpeta = Path(options["salida"] or (Path(settings.BASE_DIR) / "xlsforms"))
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / f"{codigo}.xlsx"
        wb.save(ruta)

        self.stdout.write(
            self.style.SUCCESS(
                f"Listo: {ruta} ({indicadores.count()} indicador(es)).\n"
                f"form_id: {form_id}  |  versión: {version}\n"
                "Súbelo en ODK Central: Proyecto → Formularios → Subir formulario. "
                "Si ya existe, subir de nuevo con la nueva versión lo actualiza."
            )
        )
