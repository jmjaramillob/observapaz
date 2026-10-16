import core.models
import django.db.models.deletion
from django.db import migrations, models


def copiar_soportes_existentes(apps, schema_editor):
    """Cada archivo_soporte que ya existía pasa a ser una evidencia del caso."""
    Caso = apps.get_model("core", "CasoVictimizante")
    Evidencia = apps.get_model("core", "EvidenciaCaso")
    for caso in Caso.objects.exclude(archivo_soporte="").exclude(archivo_soporte__isnull=True):
        nombre = caso.archivo_soporte.name
        base = nombre.rsplit("/", 1)[-1]
        ext = base.rsplit(".", 1)[-1].lower() if "." in base else ""
        Evidencia.objects.create(
            caso=caso,
            archivo=nombre,
            nombre_original=base,
            tipo="foto" if ext in ("jpg", "jpeg", "png") else "documento",
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_alter_casovictimizante_archivo_soporte"),
    ]

    operations = [
        migrations.CreateModel(
            name="EvidenciaCaso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("archivo", models.FileField(max_length=300, upload_to=core.models._ruta_evidencia)),
                ("nombre_original", models.CharField(blank=True, max_length=255)),
                ("tipo", models.CharField(choices=[("foto", "Foto"), ("documento", "Documento")], default="documento", max_length=10)),
                ("tamano_bytes", models.PositiveIntegerField(default=0)),
                ("origen_odk", models.CharField(blank=True, max_length=255, verbose_name="Nombre del adjunto en ODK Central")),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("caso", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="evidencias", to="core.casovictimizante")),
            ],
            options={
                "verbose_name": "Evidencia del caso",
                "verbose_name_plural": "Evidencias del caso",
                "ordering": ["id"],
            },
        ),
        migrations.AddField(
            model_name="envioodk",
            name="error",
            field=models.TextField(blank=True, help_text="Último error al convertir el envío en caso (vacío si no hubo)."),
        ),
        migrations.AddField(
            model_name="envioodk",
            name="caso",
            field=models.ForeignKey(
                blank=True, null=True,
                help_text="Caso creado a partir de este envío (permite reintentar adjuntos).",
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="envios_odk", to="core.casovictimizante",
            ),
        ),
        migrations.RunPython(copiar_soportes_existentes, migrations.RunPython.noop),
    ]
