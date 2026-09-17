import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Max, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render

from core.models import CategoriaIndicador, Indicador, Observatorio, RegistroIndicador

from .forms import RegistroPublicoForm


# ---------------------------------------------------------------------------
# ZONA PÚBLICA: formularios de captura (sin login, accesibles por enlace)
# ---------------------------------------------------------------------------


def lista_formularios(request):
    """Índice público con el enlace al formulario de cada observatorio."""
    observatorios = Observatorio.objects.filter(activo=True).order_by("codigo")
    return render(request, "panel/formularios_lista.html", {"observatorios": observatorios})


def formulario_publico(request, codigo=None):
    """
    Formulario de captura abierto. Si se entra con el código de un
    observatorio (ej. /formulario/OBS-001/), solo muestra sus indicadores.
    """
    observatorio = None
    if codigo:
        observatorio = get_object_or_404(Observatorio, codigo__iexact=codigo, activo=True)

    if request.method == "POST":
        form = RegistroPublicoForm(request.POST, observatorio=observatorio)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Gracias! El registro se guardó correctamente.")
            return redirect(request.path)
    else:
        form = RegistroPublicoForm(observatorio=observatorio)

    return render(
        request,
        "panel/formulario_publico.html",
        {"form": form, "observatorio": observatorio},
    )


# ---------------------------------------------------------------------------
# ZONA PRIVADA: dashboard con indicadores y gráficos (requiere login)
# ---------------------------------------------------------------------------


@login_required
def dashboard(request):
    """Tablero consolidado de la Red. Solo para usuarios autenticados."""
    observatorio_id = request.GET.get("observatorio")

    observatorios = Observatorio.objects.filter(activo=True).order_by("codigo")

    indicadores = Indicador.objects.select_related("observatorio", "categoria").filter(
        activo=True
    )
    registros = RegistroIndicador.objects.all()

    if observatorio_id:
        indicadores = indicadores.filter(observatorio_id=observatorio_id)
        registros = registros.filter(indicador__observatorio_id=observatorio_id)

    indicadores = indicadores.annotate(
        ultimo_valor=Max("registros__valor"),
        promedio=Avg("registros__valor"),
        total_registros=Count("registros"),
    )

    # --- Gráfico 1: registros por observatorio (barras) ---
    por_observatorio = (
        Observatorio.objects.filter(activo=True)
        .annotate(total=Count("indicadores__registros"))
        .order_by("codigo")
    )
    g_obs_labels = [o.codigo for o in por_observatorio]
    g_obs_data = [o.total for o in por_observatorio]

    # --- Gráfico 2: distribución por categoría (dona) ---
    por_categoria = (
        CategoriaIndicador.objects.annotate(total=Count("indicadores__registros"))
        .filter(total__gt=0)
        .order_by("-total")
    )
    g_cat_labels = [c.nombre for c in por_categoria]
    g_cat_data = [c.total for c in por_categoria]

    # --- Gráfico 3: evolución mensual de registros (línea) ---
    por_mes = (
        registros.annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(total=Count("id"))
        .order_by("mes")
    )
    g_mes_labels = [r["mes"].strftime("%Y-%m") for r in por_mes if r["mes"]]
    g_mes_data = [r["total"] for r in por_mes if r["mes"]]

    contexto = {
        "observatorios": observatorios,
        "indicadores": indicadores,
        "observatorio_seleccionado": int(observatorio_id) if observatorio_id else None,
        "total_observatorios": observatorios.count(),
        "total_indicadores": indicadores.count(),
        "total_registros": registros.count(),
        "g_obs_labels": json.dumps(g_obs_labels),
        "g_obs_data": json.dumps(g_obs_data),
        "g_cat_labels": json.dumps(g_cat_labels),
        "g_cat_data": json.dumps(g_cat_data),
        "g_mes_labels": json.dumps(g_mes_labels),
        "g_mes_data": json.dumps(g_mes_data),
    }
    return render(request, "panel/dashboard.html", contexto)


@login_required
def detalle_indicador(request, indicador_id):
    """Tablero individual de un indicador: su serie histórica."""
    indicador = get_object_or_404(
        Indicador.objects.select_related("observatorio", "categoria"), pk=indicador_id
    )
    registros = indicador.registros.order_by("fecha")

    contexto = {
        "indicador": indicador,
        "registros": registros,
        "fechas": json.dumps([r.fecha.isoformat() for r in registros]),
        "valores": json.dumps([r.valor for r in registros]),
        "meta": indicador.meta,
    }
    return render(request, "panel/detalle_indicador.html", contexto)
