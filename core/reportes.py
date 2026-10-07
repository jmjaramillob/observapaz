"""
Generación del reporte PDF de un caso victimizante individual.

Se usa reportlab (pura Python, sin dependencias de sistema como
wkhtmltopdf/weasyprint) para no tener que tocar el Dockerfile. El PDF
incluye el mismo encabezado institucional del resto del sitio y todos
los campos visibles en la página de detalle del caso.
"""

import io
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

CARPETA_LOGOS = settings.BASE_DIR / "panel" / "static" / "panel" / "img"

# (archivo, alto máximo en mm) -ancho se escala proporcionalmente, igual
# que en el encabezado de las páginas del sitio (Opción B: tamaño
# literal de cada logo, sin recortarlos a una altura uniforme).
LOGOS_IZQUIERDA = [
    ("logopresidencia.png", 14),
    ("logofondopaz.png", 14),
    ("Logo_Oficial_Unicartagena.png", 14),
]
LOGO_DERECHA = ("logoproyecto.png", 16)


def _imagen_logo(nombre_archivo, alto_mm):
    ruta = CARPETA_LOGOS / nombre_archivo
    if not ruta.exists():
        return None
    img = Image(str(ruta))
    escala = (alto_mm * mm) / img.imageHeight
    img.drawHeight = alto_mm * mm
    img.drawWidth = img.imageWidth * escala
    return img


def _fila_encabezado():
    """Reconstruye, en el PDF, el mismo encabezado institucional del
    sitio: los tres logos de la izquierda y el de Reparación
    Transformadora a la derecha."""
    celda_izquierda = []
    for archivo, alto in LOGOS_IZQUIERDA:
        img = _imagen_logo(archivo, alto)
        if img:
            celda_izquierda.append(img)

    celda_derecha = _imagen_logo(*LOGO_DERECHA)

    if not celda_izquierda and not celda_derecha:
        return None

    fila_izq = Table([celda_izquierda], colWidths=[None] * len(celda_izquierda)) if celda_izquierda else Paragraph("", getSampleStyleSheet()["Normal"])
    tabla = Table(
        [[fila_izq, celda_derecha or ""]],
        colWidths=[130 * mm, 40 * mm],
    )
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return tabla


def _valor(valor, por_defecto="—"):
    if valor in (None, "", []):
        return por_defecto
    return str(valor)


def generar_pdf_caso(caso):
    """
    Devuelve el PDF del reporte de un caso, como bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=18 * mm, bottomMargin=16 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )

    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloReporte", parent=estilos["Title"], fontSize=15, spaceAfter=2,
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloReporte", parent=estilos["Normal"], fontSize=9,
        textColor=colors.HexColor("#555555"), spaceAfter=10,
    )
    estilo_seccion = ParagraphStyle(
        "SeccionReporte", parent=estilos["Heading3"], fontSize=11,
        textColor=colors.HexColor("#0d6efd"), spaceBefore=10, spaceAfter=4,
    )
    estilo_texto = estilos["BodyText"]
    estilo_advertencia = ParagraphStyle(
        "AdvertenciaReserva", parent=estilos["BodyText"], fontSize=9,
        textColor=colors.HexColor("#664d03"), backColor=colors.HexColor("#fff3cd"),
        borderPadding=6, spaceBefore=4, spaceAfter=10,
    )
    estilo_pie = ParagraphStyle(
        "PieReporte", parent=estilos["Normal"], fontSize=7.5,
        textColor=colors.HexColor("#888888"),
    )

    elementos = []

    encabezado = _fila_encabezado()
    if encabezado:
        elementos.append(encabezado)
        elementos.append(Spacer(1, 8 * mm))

    elementos.append(Paragraph("Reporte de caso registrado", estilo_titulo))
    elementos.append(Paragraph(
        "Red de Observatorios — OBSERVAPAZ · "
        "Reparación Transformadora, Paz Total",
        estilo_subtitulo,
    ))

    if caso.requiere_reserva:
        elementos.append(Paragraph(
            "<b>Aviso de reserva:</b> este caso está marcado con reserva "
            "de la información. Dale un manejo cuidadoso y restringe su "
            "distribución a los fines de verificación y seguimiento del "
            "observatorio.",
            estilo_advertencia,
        ))

    # --- Datos generales ---
    datos_generales = [
        ["Observatorio", f"{caso.observatorio.codigo} — {caso.observatorio.nombre}"],
        ["Tipo de hecho", _valor(caso.tipo_hecho_otro if caso.tipo_hecho_otro else str(caso.tipo_hecho))],
        ["Fecha del hecho", _valor(caso.fecha_hecho)],
        ["Zona", _valor(caso.get_zona_display())],
        ["Vereda/corregimiento/barrio", _valor(caso.vereda_corregimiento_barrio)],
        ["Presunto responsable", _valor(
            f"{caso.get_presunto_responsable_display()} {caso.presunto_responsable_detalle}".strip()
        )],
        ["Fuente", _valor(caso.fuente)],
        ["Nivel de verificación", _valor(caso.get_nivel_verificacion_display())],
        ["Estado de revisión", _valor(caso.get_estado_display())],
    ]
    elementos.append(Paragraph("Datos generales", estilo_seccion))
    elementos.append(_tabla_campos(datos_generales))

    # --- Población afectada ---
    poblacion = [
        ["Personas afectadas", _valor(caso.num_personas_afectadas, "0")],
        ["Hombres", _valor(caso.num_hombres, "0")],
        ["Mujeres", _valor(caso.num_mujeres, "0")],
        ["Otro género", _valor(caso.num_otro_genero, "0")],
        ["Niños, niñas y adolescentes", _valor(caso.num_ninos_adolescentes, "0")],
        ["Adultos", _valor(caso.num_adultos, "0")],
        ["Adultos mayores", _valor(caso.num_adultos_mayores, "0")],
        ["Familias afectadas", _valor(caso.num_familias_afectadas, "0")],
    ]
    elementos.append(Paragraph("Población afectada", estilo_seccion))
    elementos.append(_tabla_campos(poblacion))

    # --- Descripción y afectaciones ---
    elementos.append(Paragraph("Descripción", estilo_seccion))
    elementos.append(Paragraph(_valor(caso.descripcion, "Sin descripción."), estilo_texto))

    if caso.afectaciones_materiales:
        elementos.append(Paragraph("Afectaciones materiales", estilo_seccion))
        elementos.append(Paragraph(caso.afectaciones_materiales, estilo_texto))

    if caso.necesidades_identificadas:
        elementos.append(Paragraph("Necesidades identificadas", estilo_seccion))
        elementos.append(Paragraph(caso.necesidades_identificadas, estilo_texto))

    if caso.archivo_soporte:
        elementos.append(Paragraph("Documento de soporte", estilo_seccion))
        elementos.append(Paragraph(Path(caso.archivo_soporte.name).name, estilo_texto))

    # --- Consentimiento y diligenciamiento ---
    consentimiento = [
        ["Autorización de registro", caso.autorizacion_registro and "Sí" or "No"],
        ["Requiere reserva", caso.requiere_reserva and "Sí" or "No"],
        ["Diligenciado por", _valor(f"{caso.diligencia_nombre} {caso.diligencia_rol}".strip())],
    ]
    elementos.append(Paragraph("Consentimiento y diligenciamiento", estilo_seccion))
    elementos.append(_tabla_campos(consentimiento))

    # --- Seguimiento ---
    seguimiento = [
        ["Remitido a", _valor(caso.remitido_a)],
        ["Estado del seguimiento", _valor(caso.get_estado_seguimiento_display())],
        ["Observaciones de seguimiento", _valor(caso.observaciones_seguimiento)],
    ]
    elementos.append(Paragraph("Seguimiento", estilo_seccion))
    elementos.append(_tabla_campos(seguimiento))

    if caso.revisado_por:
        texto_revision = f"Revisado por {caso.revisado_por.get_username()} el {caso.revisado_en:%Y-%m-%d %H:%M}."
        if caso.motivo_rechazo:
            texto_revision += f" Motivo de rechazo: {caso.motivo_rechazo}"
        elementos.append(Paragraph("Revisión", estilo_seccion))
        elementos.append(Paragraph(texto_revision, estilo_texto))

    elementos.append(Spacer(1, 10 * mm))
    elementos.append(Paragraph(
        f"Caso N.º {caso.id} · Generado automáticamente por OBSERVAPAZ el "
        f"{timezone.localtime():%Y-%m-%d %H:%M}.",
        estilo_pie,
    ))

    doc.build(elementos)
    return buffer.getvalue()


def _tabla_campos(filas):
    tabla = Table(
        [[Paragraph(f"<b>{etiqueta}</b>", getSampleStyleSheet()["BodyText"]), Paragraph(valor, getSampleStyleSheet()["BodyText"])]
         for etiqueta, valor in filas],
        colWidths=[55 * mm, 115 * mm],
    )
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tabla
