"""Descarga de Carteras Agregadas mediante motor de concurrencia.

Este módulo implementa el flujo de negocio para obtener la composición 
agregada de las carteras, particionando el almacenamiento por año y periodo.

API pública:
    - descargar_carteras: Punto de entrada para un periodo único.
    - descargar_carteras_rango: Wrapper para procesamiento masivo anual.
"""

from __future__ import annotations

import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .config import BASE_URL, DEFAULT_CARTERAS_INVERSIONES_AGREGADA_DIR
from .session import crear_sesion
from .cuadros_utils import descargar_y_guardar_cuadros
from .logger import configurar_logger

logger = configurar_logger(__name__)


def descargar_carteras(
    periodo: str,
    base_dir: str = DEFAULT_CARTERAS_INVERSIONES_AGREGADA_DIR,
    max_workers: int = 5,
) -> None:
    """Descarga de forma concurrente todas las carteras de un periodo mensual.

    Args:
        periodo: Identificador temporal en formato YYYYMM.
        base_dir: Directorio raíz de almacenamiento (Dataset).
        max_workers: Número de descargas simultáneas de cuadros.
    """
    # Lógica de particionamiento cronológico
    anio = periodo[:4]
    html_dir = os.path.join(base_dir, anio, "html", periodo)
    csv_dir = os.path.join(base_dir, anio, "csv", periodo)

    session = crear_sesion()

    # URL intermedia que contiene la lista de links a cuadros individuales
    url_intermedia = (
        f"{BASE_URL}/apps/loadCarteras/loadCarAgr.php"
        f"?menu=sci&menuN1=estfinfp&menuN2=NOID"
        f"&orden=20&periodo={periodo}&ext=.php"
    )

    try:
        response = session.get(url_intermedia, timeout=30)
        response.raise_for_status()
    except Exception as e:
        logger.error("[CARTERAS %s] Error crítico al acceder al índice: %s", periodo, e)
        return

    # Extracción de links mediante CSS Selectors
    soup = BeautifulSoup(response.text, "html.parser")
    links = [
        urljoin(BASE_URL, a["href"])
        for a in soup.find_all("a", title="Html", href=True)
        if "genera_xsl_v2.0.php" in a["href"]
    ]

    if not links:
        logger.warning("[CARTERAS %s] No se detectaron cuadros para este periodo.", periodo)
        return

    # Delegación al motor de concurrencia
    descargar_y_guardar_cuadros(
        session=session,
        links=links,
        html_dir=html_dir,
        csv_dir=csv_dir,
        logger=logger,
        contexto=f"CARTERAS {periodo}",
        max_workers=max_workers
    )

def descargar_carteras_rango(
    desde_anio: int,
    hasta_anio: int,
    base_dir: str = DEFAULT_CARTERAS_INVERSIONES_AGREGADA_DIR,
    max_workers: int = 5,
) -> None:
    """Procesamiento por lotes para rangos multi-anuales."""
    for anio in range(desde_anio, hasta_anio + 1):
        for mes in range(1, 13):
            periodo = f"{anio}{mes:02d}"
            descargar_carteras(periodo, base_dir=base_dir, max_workers=max_workers)