from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PerfilUsuario, RegistroIndicador


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    """
    Cada vez que se crea un usuario nuevo (incluido un superusuario),
    le crea automáticamente un PerfilUsuario vacío (sin observatorio
    asignado = ve toda la Red). Así siempre hay un perfil para editar
    desde el admin, sin pasos manuales adicionales.
    """
    if created:
        PerfilUsuario.objects.get_or_create(usuario=instance)


@receiver(user_logged_in)
def marcar_login_reciente(sender, request, user, **kwargs):
    """
    Deja una marca en la sesión para que la primera página que se
    cargue después de iniciar sesión pueda mostrar el aviso emergente
    de novedades pendientes. La vista que lo use debe "consumirla"
    (session.pop) para que no vuelva a aparecer hasta el próximo login.
    """
    request.session["mostrar_aviso_pendientes"] = True


@receiver(post_save, sender=RegistroIndicador)
def avisar_gestor_nuevo_pendiente(sender, instance, created, **kwargs):
    """
    Cuando llega un registro nuevo que queda PENDIENTE (típicamente
    desde el formulario público, sin login), le avisa por correo a
    todos los usuarios ligados a ese observatorio, para que entren a
    revisarlo y decidan si es válido.

    Si el correo no está configurado o falla, no interrumpe el guardado
    del registro (fail_silently=True): que llegue o no el aviso nunca
    debe bloquear que alguien pueda reportar una novedad.
    """
    if not created or instance.estado != RegistroIndicador.EstadoRegistro.PENDIENTE:
        return

    observatorio = instance.indicador.observatorio
    destinatarios = list(
        PerfilUsuario.objects.filter(observatorio=observatorio)
        .exclude(usuario__email="")
        .values_list("usuario__email", flat=True)
    )
    if not destinatarios:
        return

    enlace = f"{settings.SITIO_URL_BASE}/tablero/"
    send_mail(
        subject=f"[OBSERVAPAZ] Nuevo registro pendiente de revisión en {observatorio.codigo}",
        message=(
            f"Llegó un nuevo registro en el indicador «{instance.indicador.nombre}» "
            f"del observatorio {observatorio.codigo} - {observatorio.nombre}.\n\n"
            f"Fecha: {instance.fecha}\n"
            f"Valor: {instance.valor}\n"
            f"Fuente: {instance.fuente or 'No especificada'}\n\n"
            "Este registro todavía NO cuenta en los tableros oficiales. "
            "Ingresa a tu tablero para revisarlo y decidir si es válido:\n"
            f"{enlace}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=destinatarios,
        fail_silently=True,
    )
