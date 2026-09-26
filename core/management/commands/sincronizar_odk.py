from django.conf import settings
from django.core.management.base import BaseCommand

import requests

from core.models import CasoVictimizante, EnvioODK, Observatorio, TipoHecho


def _si_no_a_booleano(valor):
    if valor == "si":
        return True
    if valor == "no":
        return False
    return None


def _entero_o_none(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


class Command(BaseCommand):
    help = (
        "Trae los envíos nuevos desde ODK Central (uno por observatorio, "
        "según su form_id) y los convierte en CasoVictimizante pendiente "
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
            form_id = f"observapaz_caso_{observatorio.codigo.lower().replace('-', '_')}"
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

        self._convertir_a_caso(observatorio, envio_odk, envio)
        return True

    def _convertir_a_caso(self, observatorio, envio_odk, envio):
        tipo_hecho = None
        try:
            tipo_hecho = TipoHecho.objects.get(pk=envio.get("tipo_hecho"))
        except (TipoHecho.DoesNotExist, TypeError, ValueError):
            self.stderr.write(
                self.style.WARNING(
                    f"Envío {envio_odk.envio_id}: el tipo de hecho '{envio.get('tipo_hecho')}' "
                    "no existe -queda guardado en EnvioODK sin convertir, para revisarlo a mano-."
                )
            )
            return

        CasoVictimizante.objects.create(
            observatorio=observatorio,
            fecha_hecho=envio.get("fecha_hecho"),
            vereda_corregimiento_barrio=envio.get("vereda_corregimiento_barrio") or "",
            zona=envio.get("zona") or "",
            tipo_hecho=tipo_hecho,
            tipo_hecho_otro=envio.get("tipo_hecho_otro") or "",
            presunto_responsable=envio.get("presunto_responsable") or "",
            presunto_responsable_detalle=envio.get("presunto_responsable_detalle") or "",
            num_personas_afectadas=_entero_o_none(envio.get("num_personas_afectadas")),
            num_hombres=_entero_o_none(envio.get("num_hombres")),
            num_mujeres=_entero_o_none(envio.get("num_mujeres")),
            num_otro_genero=_entero_o_none(envio.get("num_otro_genero")),
            num_ninos_adolescentes=_entero_o_none(envio.get("num_ninos_adolescentes")),
            num_adultos=_entero_o_none(envio.get("num_adultos")),
            num_adultos_mayores=_entero_o_none(envio.get("num_adultos_mayores")),
            num_familias_afectadas=_entero_o_none(envio.get("num_familias_afectadas")),
            fuente=envio.get("fuente") or "",
            nivel_verificacion=envio.get("nivel_verificacion") or CasoVictimizante.NivelVerificacion.NO_VERIFICADO,
            descripcion=envio.get("descripcion") or "",
            afectaciones_materiales=envio.get("afectaciones_materiales") or "",
            necesidades_identificadas=envio.get("necesidades_identificadas") or "",
            autorizacion_registro=bool(_si_no_a_booleano(envio.get("autorizacion_registro"))),
            requiere_reserva=(
                _si_no_a_booleano(envio.get("requiere_reserva"))
                if envio.get("requiere_reserva") is not None
                else True
            ),
            diligencia_nombre=envio.get("diligencia_nombre") or "",
            diligencia_rol=envio.get("diligencia_rol") or "",
            estado=CasoVictimizante.EstadoRevision.PENDIENTE,
        )
        envio_odk.procesado = True
        envio_odk.save(update_fields=["procesado"])
