"""
Reglas de las evidencias (fotos y documentos) de un caso.

Solo se aceptan fotos (JPG, PNG) y documentos (PDF, Word). NO se aceptan
videos. Cada archivo se valida por extensión, por tamaño y por su
contenido real (los primeros bytes), para que no se pueda subir un
archivo de otro tipo renombrándolo.
"""
from pathlib import Path

from django.core.exceptions import ValidationError

TAMANO_MAXIMO_MB = 10
MAX_ARCHIVOS_POR_CASO = 5
TAMANO_TOTAL_MAXIMO_MB = 25

# extensión -> (tipo de contenido, firma de los primeros bytes, ¿se ve en el navegador?)
FORMATOS = {
    "jpg": ("image/jpeg", (b"\xff\xd8\xff",), True),
    "jpeg": ("image/jpeg", (b"\xff\xd8\xff",), True),
    "png": ("image/png", (b"\x89PNG\r\n\x1a\n",), True),
    "pdf": ("application/pdf", (b"%PDF",), True),
    "doc": ("application/msword", (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",), False),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        (b"PK\x03\x04",),
        False,
    ),
}
EXTENSIONES_FOTO = ("jpg", "jpeg", "png")
EXTENSIONES_PERMITIDAS = tuple(FORMATOS)


def extension_de(nombre):
    return Path(nombre or "").suffix.lower().lstrip(".")


def tipo_contenido(nombre):
    formato = FORMATOS.get(extension_de(nombre))
    return formato[0] if formato else "application/octet-stream"


def se_ve_en_navegador(nombre):
    formato = FORMATOS.get(extension_de(nombre))
    return bool(formato and formato[2])


def es_foto(nombre):
    return extension_de(nombre) in EXTENSIONES_FOTO


def validar_evidencia(archivo):
    """Lanza ValidationError si el archivo no es una foto o documento válido."""
    nombre = getattr(archivo, "name", "") or ""
    ext = extension_de(nombre)
    if ext not in FORMATOS:
        raise ValidationError(
            f"«{Path(nombre).name}»: tipo no permitido. Solo fotos (JPG, PNG) "
            "y documentos (PDF, Word); no se aceptan videos."
        )
    if archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024:
        raise ValidationError(
            f"«{Path(nombre).name}» supera los {TAMANO_MAXIMO_MB} MB."
        )
    posicion = archivo.tell() if hasattr(archivo, "tell") else 0
    archivo.seek(0)
    inicio = archivo.read(8)
    archivo.seek(posicion if posicion else 0)
    if not any(inicio.startswith(firma) for firma in FORMATOS[ext][1]):
        raise ValidationError(
            f"«{Path(nombre).name}»: el contenido no corresponde a un archivo .{ext}."
        )


def validar_conjunto(archivos, ya_guardados=0, bytes_guardados=0):
    """Valida cada archivo y los límites de cantidad y tamaño total."""
    if ya_guardados + len(archivos) > MAX_ARCHIVOS_POR_CASO:
        raise ValidationError(
            f"Máximo {MAX_ARCHIVOS_POR_CASO} archivos por caso."
        )
    total = bytes_guardados
    for a in archivos:
        validar_evidencia(a)
        total += a.size
    if total > TAMANO_TOTAL_MAXIMO_MB * 1024 * 1024:
        raise ValidationError(
            f"Los archivos de un caso no pueden sumar más de {TAMANO_TOTAL_MAXIMO_MB} MB."
        )
