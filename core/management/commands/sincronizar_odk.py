from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

import requests

from core.models import EnvioODK, Indicador, Observatorio, RegistroIndicador


class Command(BaseCommand):
    help = (
        "Trae los envíos nuevos desde ODK Central (uno por observatorio, "
        "según su form_id) y los convierte en RegistroIndicador pendiente "
        "de revisión -mismo flujo de moderación que el formulario web-."
    )

    def handle(self, *args, **options):
        if not all(
            [
                settings.ODK_CENTRAL_URL,
                settings.ODK_CENTRAL_EMAIL,
                settings.ODK_CENTRAL_PASSWORD,
                settings.ODK_CENTRAL_PROJECT_ID,
            ]
        ):
            self.stdout.write(
                self.style.WARNING(
                    "ODK Central no está configurado todavía (variables ODK_CENTRAL_* "
                    "vacías en el .env). No se hace nada."
                )
            )
            return

        token = self._iniciar_sesion()
        if not token:
            return

        total_nuevos = 0
        for observatorio in Observatorio.objects.filter(activo=True):
            form_id = f"observapaz_{observatorio.codigo.lower().replace('-', '_')}"
            total_nuevos += self._sincronizar_formulario(token, observatorio, form_id)

        self.stdout.write(self.style.SUCCESS(f"Listo: {total_nuevos} envío(s) nuevo(s) procesado(s)."))

    def _iniciar_sesion(self):
        url = f"{settings.ODK_CENTRAL_URL.rstrip('/')}/v1/sessions"
        try:
            resp = requests.post(
                url,
                json={"email": settings.ODK_CENTRAL_EMAIL, "password": settings.ODK_CENTRAL_PASSWORD},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()["token"]
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"No se pudo iniciar sesión en ODK Central: {e}"))
            return None

    def _sincronizar_formulario(self, token, observatorio, form_id):
        """
        Usa el feed OData de Central (.svc/Submissions), que entrega los
        envíos ya en JSON con los nombres de campo del formulario -más
        simple de leer que el XML crudo-.
        """
        base = settings.ODK_CENTRAL_URL.rstrip("/")
        proyecto = settings.ODK_CENTRAL_PROJECT_ID
        url = f"{base}/v1/projects/{proyecto}/forms/{form_id}.svc/Submissions"
        headers = {"Authorization": f"Bearer {token}"}
        nuevos = 0

        while url:
            try:
                resp = requests.get(url, headers=headers, timeout=30)
            except requests.RequestException as e:
                self.stderr.write(self.style.ERROR(f"{observatorio.codigo}: error de red ({e})."))
                return nuevos

            if resp.status_code == 404:
                # Este observatorio todavía no tiene formulario en Central
                # (no se ha subido su XLSForm) -se ignora sin marcar error-.
                return nuevos
            if not resp.ok:
                self.stderr.write(
                    self.style.ERROR(f"{observatorio.codigo}: ODK Central respondió {resp.status_code}.")
                )
                return nuevos

            datos = resp.json()
            for envio in datos.get("value", []):
                if self._procesar_envio(observatorio, form_id, envio):
                    nuevos += 1

            url = datos.get("@odata.nextLink")

        return nuevos

    def _procesar_envio(self, observatorio, form_id, envio):
        envio_id = envio.get("__id")
        if not envio_id:
            return False

        # 'envio_id' es único en nuestra tabla: si ya lo habíamos traído
        # antes, get_or_create simplemente lo encuentra y no repite nada.
        envio_odk, creado = EnvioODK.objects.get_or_create(
            envio_id=envio_id,
            defaults={
                "observatorio": observatorio,
                "formulario_id": form_id,
                "datos": envio,
            },
        )
        if not creado:
            return False

        self._convertir_a_registro(envio_odk, envio)
        return True

    def _convertir_a_registro(self, envio_odk, envio):
        try:
            indicador = Indicador.objects.get(pk=envio.get("indicador"))
        except (Indicador.DoesNotExist, TypeError, ValueError):
            self.stderr.write(
                self.style.WARNING(
                    f"Envío {envio_odk.envio_id}: el indicador '{envio.get('indicador')}' "
                    "no existe -queda guardado en EnvioODK sin convertir, para revisarlo a mano-."
                )
            )
            return

        RegistroIndicador.objects.create(
            indicador=indicador,
            fecha=envio.get("fecha"),
            valor=envio.get("valor"),
            fuente=envio.get("fuente") or "",
            observaciones=envio.get("observaciones") or "",
            ubicacion=self._extraer_punto(envio.get("ubicacion")),
            estado=RegistroIndicador.EstadoRegistro.PENDIENTE,
        )
        envio_odk.procesado = True
        envio_odk.save(update_fields=["procesado"])

    def _extraer_punto(self, valor):
        """
        ODK Central entrega el geopoint en el feed OData como un objeto
        tipo GeoJSON: {"type": "Point", "coordinates": [lon, lat, alt]}.
        Si al probarlo contra tu Central real llega en otro formato,
        este es el lugar exacto para ajustarlo.
        """
        if not valor or not isinstance(valor, dict):
            return None
        coords = valor.get("coordinates")
        if not coords or len(coords) < 2:
            return None
        lon, lat = coords[0], coords[1]
        return Point(lon, lat, srid=4326)
