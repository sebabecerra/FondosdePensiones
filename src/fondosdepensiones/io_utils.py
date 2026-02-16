"""
Utilidades de entrada/salida (HTML y CSV) – FIX SPensiones

OBJETIVO:
---------
Preservar el HTML EXACTAMENTE como viene desde SPensiones y
convertir SOLO los números dentro de las celdas:

    1.234,56  →  1234.56
    12.345    →  12345
    123,4     →  123.4

SIN:
    - modificar texto
    - modificar encabezados
    - modificar atributos HTML
    - modificar href, id, etc.

Pipeline:
---------
HTML original
        ↓
Transformación SOLO de números en nodos de texto
        ↓
pandas.read_html()
        ↓
CSV correcto (utf-8-sig)
"""

import os
import re
from io import StringIO
import pandas as pd
from bs4 import BeautifulSoup
from .logger import configurar_logger

logger = configurar_logger(__name__)

# =============================================================================
# REGEX PARA DETECTAR NUMEROS ESTILO CHILE
# =============================================================================
_RE_CH_NUM = re.compile(
    r"\b\d{1,3}(?:\.\d{3})*(?:,\d+)?\b|\b\d+(?:,\d+)\b|\b\d+\b"
)

# =============================================================================
# CONVERSIÓN DE TOKEN NUMÉRICO
# =============================================================================
def _to_float_token(token: str) -> str:
    """
    Convierte:

        1.234,56 → 1234.56
        12.345   → 12345
        12,3     → 12.3
    """
    t = token.strip()
    t = t.replace(".", "").replace(",", ".")
    return t


def _transformar_solo_numeros_en_texto(text: str) -> str:
    """
    Reemplaza SOLO números dentro de un texto.
    """

    def _repl(m):
        return _to_float_token(m.group(0))

    return _RE_CH_NUM.sub(_repl, text)


def _html_transformar_solo_numeros(html: str) -> str:
    """
    Recorre el HTML y transforma SOLO números dentro de nodos de texto.

    NO modifica:
        - atributos
        - href
        - clases
        - etiquetas
    """

    soup = BeautifulSoup(html, "html.parser")

    for node in soup.find_all(string=True):

        if node.parent.name in ("script", "style"):
            continue

        original = str(node)

        if not original.strip():
            continue

        nuevo = _transformar_solo_numeros_en_texto(original)

        if nuevo != original:
            node.replace_with(nuevo)

    return str(soup)


# =============================================================================
# GUARDADO HTML + CSV
# =============================================================================
def guardar_html_y_csv(
    html: str,
    nombre: str,
    html_dir: str,
    csv_dir: str
) -> None:

    os.makedirs(html_dir, exist_ok=True)
    os.makedirs(csv_dir, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1) Guardar HTML ORIGINAL (intacto)
    # -------------------------------------------------------------------------
    html_path = os.path.join(html_dir, f"{nombre}.html")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    try:
        # ---------------------------------------------------------------------
        # 2) Crear copia SOLO para parseo numérico
        # ---------------------------------------------------------------------
        html_transformado = _html_transformar_solo_numeros(html)

        # ---------------------------------------------------------------------
        # 3) Leer tabla
        # SPensiones suele tener doble header
        # ---------------------------------------------------------------------
        try:
            tablas = pd.read_html(StringIO(html_transformado), header=[0, 1])
        except Exception:
            tablas = pd.read_html(StringIO(html_transformado), header=0)

        if not tablas:
            logger.warning("[%s] No se detectaron tablas.", nombre)
            return

        df = tablas[0].copy()

        # ---------------------------------------------------------------------
        # 4) Convertir SOLO columnas numéricas
        # Primera columna = categoría
        # ---------------------------------------------------------------------
        for col in df.columns[1:]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # ---------------------------------------------------------------------
        # 5) Guardar CSV final
        # ---------------------------------------------------------------------
        csv_path = os.path.join(csv_dir, f"{nombre}.csv")

        df.to_csv(
            csv_path,
            index=False,
            encoding="utf-8-sig"
        )

        logger.debug(
            "[%s] CSV generado correctamente (%d filas, %d cols).",
            nombre,
            df.shape[0],
            df.shape[1]
        )

    except Exception as e:
        logger.error(
            "[%s] Error crítico al procesar tabla: %s",
            nombre,
            e
        )