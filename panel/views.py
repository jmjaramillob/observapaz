from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Indicador, Observatorio
from core.utils import observatorio_del_usuario


# ---------------------------------------------------------------------------
# ZONA PÚBLICA: formularios de captura (sin login, accesibles por enlace)
# ---------------------------------------------------------------------------


def lista_formularios(request):
    """
    Índice público con el enlace al formulario de cada observatorio.
    Si se entra desde el subdominio propio de un observatorio (ej.
    obs-007.observapaz.org), no tiene sentido mostrarle la lista de
    los 24 -se manda directo a SU formulario-.
    """
    if request.observatorio:
        return redirect("panel:formulario_publico", codigo=request.observatorio.codigo)

    observatorios = Observatorio.objects.filter(activo=True).order_by("codigo")
    return render(request, "panel/formularios_lista.html", {"observatorios": observatorios})


def formulario_publico(request, codigo=None):
    """
    Muestra el formulario de captura. El HTML solo sirve de "cascarón":
    la lista de indicadores se carga con JavaScript desde
    GET /api/indicadores/, y el envío se hace con POST /api/registros/
    -Django ya no procesa el formulario aquí-.

    El observatorio se resuelve así, en orden: el código explícito en
    la URL (/formulario/OBS-007/) si alguien lo visita directamente;
    si no hay código en la URL, el del subdominio (obs-007.dominio),
    si aplica.
    """
    observatorio = None
    if codigo:
        observatorio = get_object_or_404(Observatorio, codigo__iexact=codigo, activo=True)
    elif request.observatorio:
        observatorio = request.observatorio

    return render(
        request,
        "panel/formulario_publico.html",
        {"observatorio": observatorio},
    )


# ---------------------------------------------------------------------------
# ZONA PRIVADA: tablero (requiere login). Django solo protege el acceso
# y le dice al JavaScript a qué observatorio está limitado el usuario;
# los datos en sí los trae la página con fetch() contra la API.
# ---------------------------------------------------------------------------


def tablero_publico(request):
    """
    Tablero consolidado PÚBLICO (sin login). Cifras agregadas, vía API.
    Desde el subdominio de un observatorio muestra sus propias cifras
    por defecto (con un enlace para ver el consolidado de toda la Red);
    desde el dominio raíz, muestra la Red completa.
    """
    contexto = {"obs_subdominio": request.observatorio, "dominio_base": settings.DOMINIO_BASE}
    return render(request, "panel/tablero_publico.html", contexto)


@login_required
def tablero(request):
    """
    Tablero privado. Si el usuario pertenece a un observatorio, el
    JavaScript queda limitado a consultar solo esos datos (la API,
    de todas formas, lo exigiría aunque el HTML intentara pedir otra
    cosa) -esto NUNCA lo decide el subdominio, solo el PerfilUsuario-.
    Si es de coordinación, puede moverse entre los 24, y si entró desde
    el subdominio de un observatorio, el filtro arranca ya puesto ahí
    (puede cambiarlo igual).

    Como esta es la página a la que redirige el login, aquí es donde se
    "consume" la marca de sesión que dispara el aviso emergente de
    novedades pendientes -session.pop la borra, para que no vuelva a
    aparecer hasta el próximo inicio de sesión-.
    """
    obs_usuario = observatorio_del_usuario(request.user)
    contexto = {
        "obs_usuario": obs_usuario,
        "puede_filtrar": obs_usuario is None,
        "obs_subdominio": request.observatorio if obs_usuario is None else None,
        "mostrar_aviso_pendientes": request.session.pop("mostrar_aviso_pendientes", False),
    }
    return render(request, "panel/tablero_privado.html", contexto)


@login_required
def novedades(request):
    """
    Bandeja de novedades pendientes: la página dedicada a revisarlas y
    decidir si son válidas (a diferencia del tablero, que solo muestra
    un resumen con el enlace hacia aquí).
    """
    return render(request, "panel/novedades.html")


@login_required
def detalle_indicador(request, indicador_id):
    """
    Tablero individual de un indicador. Django sigue siendo quien
    decide si el usuario puede ENTRAR a esta página (404 si el
    indicador es de otro observatorio) -eso no se puede dejar solo en
    manos de JavaScript, que cualquiera podría manipular-. Una vez
    dentro, el historial de valores se trae con fetch() a la API,
    que vuelve a validar el mismo acceso de forma independiente.
    """
    obs_usuario = observatorio_del_usuario(request.user)

    qs = Indicador.objects.select_related("observatorio", "categoria")
    if obs_usuario:
        qs = qs.filter(observatorio=obs_usuario)

    indicador = get_object_or_404(qs, pk=indicador_id)

    contexto = {
        "indicador": indicador,
    }
    return render(request, "panel/detalle_indicador.html", contexto)
