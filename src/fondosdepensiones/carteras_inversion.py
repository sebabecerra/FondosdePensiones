"""Descarga concurrente de Carteras de Inversión (Desagregadas)."""

from __future__ import annotations

import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import Any

from .config import BASE_URL, DEFAULT_CARTERAS_INVERSIONES_DIR
from .session import crear_sesion
from .cuadros_utils import descargar_y_guardar_cuadros
from .logger import configurar_logger

logger = configurar_logger(__name__)

def descargar_carteras_inversion(
    periodo: str,
    base_dir: str = DEFAULT_CARTERAS_INVERSIONES_DIR,
    **kwargs: Any,  # <--- RECIBE CONFIG_DESCARGA
) -> None:
    """Descarga de forma paralela las carteras desagregadas."""
    
    # Inyectamos el valor configurado por el usuario
    workers = kwargs.get("max_workers", 5)

    anio = periodo[:4]
    html_dir = os.path.join(base_dir, anio, "html", periodo)
    csv_dir = os.path.join(base_dir, anio, "csv", periodo)

    session = crear_sesion() 

    url_intermedia = (
        f"{BASE_URL}/apps/loadCarteras/loadCarInv.php"
        f"?menu=sci&menuN1=estfinfp&menuN2=NOID"
        f"&orden=10&periodo={periodo}&ext=.php"
    )

    logger.info("[CARTERAS_INVERSION %s] Obteniendo links de cuadros", periodo)

    response = session.get(url_intermedia, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    links = [
        urljoin(BASE_URL, a["href"])
        for a in soup.find_all("a", title="Html", href=True)
        if "genera_desagregada_xsl_v2.0.php" in a["href"]
    ]

    # Pasamos el parámetro de hilos al motor de persistencia
    descargar_y_guardar_cuadros(
        session=session,
        links=links,
        html_dir=html_dir,
        csv_dir=csv_dir,
        logger=logger,
        contexto=f"CARTERAS_INVERSION {periodo}",
        max_workers=workers
    )