"""
Manejo de sesiones HTTP.

Centraliza la creación de sesiones `requests.Session` para asegurar
headers consistentes y facilitar futuras mejoras (retries, proxies, etc.).
"""

import requests
from .config import BASE_URL


def crear_sesion() -> requests.Session:
    """
    Crea y configura una sesión HTTP estándar para SPensiones.

    Returns:
        requests.Session: sesión configurada con headers base.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{BASE_URL}/apps/centroEstadisticas/paginaCuadrosCCEE.php",
    })
    return session
