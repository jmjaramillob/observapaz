import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from core.models import CategoriaIndicador, Indicador, Observatorio, RegistroIndicador


class Command(BaseCommand):
    help = "Carga datos de ejemplo: 24 observatorios, categorías, indicadores y registros."

    def handle(self, *args, **options):
        categorias_nombres = [
            "Seguridad y convivencia",
            "Derechos humanos",
            "Participación comunitaria",
            "Desarrollo territorial",
            "Reincorporación",
        ]
        categorias = []
        for nombre in categorias_nombres:
            cat, _ = CategoriaIndicador.objects.get_or_create(nombre=nombre)
            categorias.append(cat)

        indicadores_base = [
            ("Casos atendidos", "casos"),
            ("Personas participantes", "personas"),
            ("Jornadas realizadas", "jornadas"),
            ("Cobertura territorial", "%"),
        ]

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

            for nombre, unidad in random.sample(indicadores_base, k=random.randint(2, 4)):
                ind, _ = Indicador.objects.get_or_create(
                    observatorio=obs,
                    nombre=nombre,
                    defaults={
                        "categoria": random.choice(categorias),
                        "unidad": unidad,
                        "meta": random.choice([50, 100, 200, None]),
                        "activo": True,
                    },
                )

                if ind.registros.exists():
                    continue

                hoy = date.today()
                for mes in range(8, 0, -1):
                    fecha = hoy - timedelta(days=mes * 30)
                    RegistroIndicador.objects.create(
                        indicador=ind,
                        fecha=fecha,
                        valor=round(random.uniform(10, 180), 1),
                        fuente=random.choice(
                            ["Visita de campo", "Acta comunitaria", "Reporte ODK", "Mesa técnica"]
                        ),
                        # Datos de ejemplo: se crean ya aprobados, para que
                        # se vean de una vez en los tableros. Los registros
                        # que lleguen por el formulario público sí quedan
                        # pendientes de revisión (comportamiento normal).
                        estado=RegistroIndicador.EstadoRegistro.APROBADO,
                    )
                    creados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Listo: {Observatorio.objects.count()} observatorios, "
                f"{Indicador.objects.count()} indicadores, "
                f"{RegistroIndicador.objects.count()} registros ({creados} nuevos)."
            )
        )
