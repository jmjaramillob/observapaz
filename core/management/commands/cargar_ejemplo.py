import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from core.models import CasoVictimizante, Observatorio, TipoHecho


class Command(BaseCommand):
    help = "Carga datos de ejemplo: 24 observatorios, catálogo de tipos de hecho, y casos aprobados."

    def handle(self, *args, **options):
        tipos_nombres = [
            "Desplazamiento forzado",
            "Homicidio",
            "Amenaza",
            "Desaparición forzada",
            "Secuestro",
            "Tortura",
            "Delitos contra la libertad e integridad sexual",
            "Reclutamiento, uso o utilización de niños, niñas y adolescentes",
            "Minas antipersonal / munición sin explotar (MAP/MUSE)",
            "Confinamiento",
            "Despojo o abandono forzado de tierras",
            "Actos terroristas / atentados / combates",
            "Extorsión",
            "Otro",
        ]
        tipos = []
        for i, nombre in enumerate(tipos_nombres):
            tipo, _ = TipoHecho.objects.get_or_create(nombre=nombre, defaults={"orden": i})
            tipos.append(tipo)

        zonas = [z for z, _ in CasoVictimizante.Zona.choices]
        responsables = [r for r, _ in CasoVictimizante.PresuntoResponsable.choices]
        verificaciones = [v for v, _ in CasoVictimizante.NivelVerificacion.choices]

        creados = 0
        for i in range(1, 25):
            obs, _ = Observatorio.objects.get_or_create(
                codigo=f"OBS-{i:03d}",
                defaults={
                    "nombre": f"Observatorio Territorial {i}",
                    "departamento": random.choice(
                        ["Bolívar", "Antioquia", "Cauca", "Nariño", "Meta", "Chocó"]
                    ),
                    "municipio": f"Municipio {i}",
                    "activo": True,
                },
            )

            if obs.casos.exists():
                continue

            hoy = date.today()
            for mes in range(8, 0, -1):
                for _ in range(random.randint(1, 3)):
                    fecha = hoy - timedelta(days=mes * 30 + random.randint(0, 25))
                    personas = random.randint(1, 40)
                    CasoVictimizante.objects.create(
                        observatorio=obs,
                        fecha_hecho=fecha,
                        zona=random.choice(zonas),
                        tipo_hecho=random.choice(tipos),
                        presunto_responsable=random.choice(responsables),
                        num_personas_afectadas=personas,
                        num_hombres=personas // 2,
                        num_mujeres=personas - (personas // 2),
                        num_familias_afectadas=max(1, personas // 4),
                        fuente=random.choice(
                            ["Visita de campo", "Acta comunitaria", "Reporte ODK", "Autoridad local"]
                        ),
                        nivel_verificacion=random.choice(verificaciones),
                        descripcion="Caso de ejemplo generado automáticamente.",
                        autorizacion_registro=True,
                        # Datos de ejemplo: se crean ya aprobados, para que se
                        # vean de una vez en los tableros. Los casos que
                        # lleguen por el formulario público o por ODK sí
                        # quedan pendientes de revisión (comportamiento normal).
                        estado=CasoVictimizante.EstadoRevision.APROBADO,
                    )
                    creados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Listo: {Observatorio.objects.count()} observatorios, "
                f"{TipoHecho.objects.count()} tipos de hecho, "
                f"{CasoVictimizante.objects.count()} casos ({creados} nuevos)."
            )
        )
