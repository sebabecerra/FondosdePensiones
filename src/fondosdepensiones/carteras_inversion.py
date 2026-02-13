"""
Descarga de Carteras de Inversión desde el sitio de la
Superintendencia de Pensiones (Chile).

Este módulo implementa el flujo completo para obtener las
Carteras de Inversión (desagregadas) para un período mensual
específico (YYYYMM).

Responsabilidades del módulo:
- Construir la URL intermedia de Carteras de Inversión.
- Extraer TODOS los links HTML disponibles.
- Delegar la descarga y persistencia (HTML + CSV) a utilidades comunes.

Decisiones de diseño:
- No imprime directamente (usa logging).
- No genera rangos de períodos (eso es responsabilidad del CLI).
- Reutiliza `cuadros_utils` para evitar duplicación.
- Mantiene API simétrica a `carteras.py`.

API pública:
- descargar_carteras_inversion(periodo, base_dir)
- descargar_carteras_inversion_rango(desde_anio, hasta_anio, base_dir)
"""

from __future__ import annotations

import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .config import BASE_URL, DEFAULT_CARTERAS_INVERSIONES_DIR
from .session import crear_sesion
from .cuadros_utils import descargar_y_guardar_cuadros
from .logger import configurar_logger

logger = configurar_logger(__name__)


# ============================================================
# API PÚBLICA – PERÍODO ÚNICO
# ============================================================
def descargar_carteras_inversion(
    periodo: str,
    base_dir: str = DEFAULT_CARTERAS_INVERSIONES_DIR,
) -> None:
    """
    Descarga las Carteras de Inversión para un período mensual específico.

    Args:
        periodo (str): Período en formato YYYYMM (ej: "202401").
        base_dir (str): Directorio base de salida.

    Flujo:
        1. Construye la URL intermedia del período.
        2. Extrae todos los links HTML disponibles.
        3. Descarga y guarda cada cuadro (HTML + CSV).
    """
    # --- NUEVA LÓGICA DE DIRECTORIOS ---
    anio = periodo[:4]  # Extrae "2024" de "202401"

    html_dir = os.path.join(base_dir, anio, "html", periodo)
    csv_dir = os.path.join(base_dir, anio, "csv", periodo)

    session = crear_sesion() 

    url_intermedia = (
        f"{BASE_URL}/apps/loadCarteras/loadCarInv.php"
        f"?menu=sci&menuN1=estfinfp&menuN2=NOID"
        f"&orden=10&periodo={periodo}&ext=.php"
    )

    logger.info("[CARTERAS_INVERSION %s] GET página intermedia", periodo)

    response = session.get(url_intermedia, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # 👇 MISMA LÓGICA QUE CARTERAS AGREGADAS
    links = [
        urljoin(BASE_URL, a["href"])
        for a in soup.find_all("a", title="Html", href=True)
        if "genera_desagregada_xsl_v2.0.php" in a["href"]
    ]

    if not links:
        logger.warning(
            "[CARTERAS_INVERSION %s] Sin links de cuadros (0)", periodo
        )
        return

    descargar_y_guardar_cuadros(
        session=session,
        links=links,
        html_dir=html_dir,
        csv_dir=csv_dir,
        logger=logger,
        contexto=f"CARTERAS_INVERSION {periodo}",
    )


# ============================================================
# API PÚBLICA – RANGO DE AÑOS
# ============================================================
def descargar_carteras_inversion_rango(
    desde_anio: int,
    hasta_anio: int,
    base_dir: str = DEFAULT_CARTERAS_INVERSIONES_DIR,
) -> None:
    """
    Descarga Carteras de Inversión para todos los meses
    de un rango de años.

    Args:
        desde_anio (int): Año inicial (inclusive).
        hasta_anio (int): Año final (inclusive).
        base_dir (str): Directorio base de salida.
    """
    for anio in range(desde_anio, hasta_anio + 1):
        for mes in range(1, 13):
            periodo = f"{anio}{mes:02d}"
            descargar_carteras_inversion(periodo, base_dir=base_dir)