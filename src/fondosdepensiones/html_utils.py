"""
Utilidades para procesamiento de HTML.

Incluye decodificación robusta, extracción de títulos y
normalización de nombres de archivo.
"""

import re
import unicodedata
import html as html_lib
from bs4 import BeautifulSoup
import requests


def decode_html(resp: requests.Response) -> str:
    """
    Decodifica contenido HTML de forma robusta.

    Args:
        resp (requests.Response): respuesta HTTP.

    Returns:
        str: HTML decodificado correctamente.
    """
    raw = resp.content

    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass

    enc = (resp.apparent_encoding or "").lower().strip()
    if enc:
        try:
            return raw.decode(enc, errors="replace")
        except Exception:
            pass

    return raw.decode("latin1", errors="replace")


def extraer_titulo(html: str, fallback: str) -> str:
    """
    Extrae el título desde un <h3> del HTML.

    Args:
        html (str): contenido HTML.
        fallback (str): valor por defecto si no existe <h3>.

    Returns:
        str: título extraído o fallback.
    """
    soup = BeautifulSoup(html, "html.parser")
    h3 = soup.find("h3")
    return h3.get_text(" ", strip=True) if h3 else fallback


def limpiar_nombre(texto: str, max_len: int = 180) -> str:
    """
    Normaliza un texto para usarlo como nombre de archivo.

    Args:
        texto (str): texto original.
        max_len (int): longitud máxima permitida.

    Returns:
        str: nombre limpio y seguro para filesystem.
    """
    texto = html_lib.unescape(texto).strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")

    texto = re.sub(r"[^\w\s-]", "", texto)
    texto = re.sub(r"\s+", "_", texto)
    texto = re.sub(r"_+", "_", texto)

    return texto.lower()[:max_len].strip("_")
