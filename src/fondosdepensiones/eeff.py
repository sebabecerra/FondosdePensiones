"""Descarga concurrente de Estados Financieros (EEFF) del Fondo.

Este módulo implementa la lógica de negocio para obtener los estados financieros 
trimestrales, particionando la salida por año y periodo.
"""

from __future__ import annotations

import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import Any

from .config import BASE_URL, DEFAULT_EEFF_DIR
from .session import crear_sesion
from .cuadros_utils import descargar_y_guardar_cuadros
from .logger import configurar_logger

logger = configurar_logger(__name__)

def descargar_eeff(
    periodo: str,
    base_dir: str = DEFAULT_EEFF_DIR,
    **kwargs: Any,  # <--- CAPTURA EL CONFIG_DESCARGA DEL CLI
) -> None:
    """Descarga los cuadros de eeff usando el motor multi-hilo.

    Args:
        periodo: Formato YYYYMM.
        base_dir: Ruta raíz de Estados Financieros.
        **kwargs: Saco de configuración dinámica (max_workers, etc.).
    """
    # 1. Extracción de configuración de performance
    workers = kwargs.get("max_workers", 5)

    # 2. Jerarquía cronológica: data/EEFF/YYYY/formato/periodo
    anio = periodo[:4]
    html_dir = os.path.join(base_dir, anio, "html", periodo)
    csv_dir = os.path.join(base_dir, anio, "csv", periodo)

    session = crear_sesion()

    url_intermedia = (
        f"{BASE_URL}/apps/loadEstadisticas/loadFecuFondo.php"
        f"?menu=sci&menuN1=estfinfp&menuN2=NOID"
        f"&orden=30&periodo={periodo}&ext=.php"
    )

    response = session.get(url_intermedia, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Extracción de links desde la estructura de pestañas de eeff
    links: list[str] = []
    for tab in soup.select('div.tab-pane[id^="idu_"]'):
        for a in tab.select('a[href*="loadCuadroFecuFondo.php"]'):
            href = a.get("href")
            if "tipo=html" in href:
                links.append(urljoin(url_intermedia, href))

    # 3. CABLEADO: Pasamos los workers reales al motor de cuadros_utils
    descargar_y_guardar_cuadros(
        session=session,
        links=links,
        html_dir=html_dir,
        csv_dir=csv_dir,
        logger=logger,
        contexto=f"EEFF {periodo}",
        max_workers=workers
    )