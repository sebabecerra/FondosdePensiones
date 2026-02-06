"""
Descarga de eeff Fondo desde el sitio de la Superintendencia de Pensiones (Chile).

Este módulo implementa el flujo completo para obtener los estados eeff Fondo
para un período mensual específico (YYYYMM).

Responsabilidades del módulo:
- Construir la URL intermedia de eeff Fondo para un período dado.
- Navegar la estructura de pestañas del HTML intermedio.
- Extraer los links HTML de los cuadros eeff.
- Delegar la descarga y persistencia de cada cuadro (HTML + CSV)
  a utilidades comunes reutilizables.

Decisiones de diseño:
- Mantiene la misma estructura y flujo que `carteras.py`.
- Las diferencias se limitan exclusivamente a:
  - URL intermedia.
  - Forma de extraer los links HTML.
- No imprime ni configura logging directamente.

API pública:
- descargar_eeff(periodo, base_dir)
- descargar_eeff_rango(desde_anio, hasta_anio, base_dir)
"""

from __future__ import annotations

import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .config import BASE_URL, DEFAULT_EEFF_DIR
from .session import crear_sesion
from .cuadros_utils import descargar_y_guardar_cuadros

from .logger import configurar_logger

logger = configurar_logger(__name__)



# ============================================================
# API PÚBLICA – PERÍODO ÚNICO
# ============================================================
def descargar_eeff(
    periodo: str,
    base_dir: str = DEFAULT_EEFF_DIR,
) -> None:
    """
    Descarga los estados eeff Fondo para un período mensual específico.

    Args:
        periodo (str): Período en formato YYYYMM (ej: "202401").
        base_dir (str): Directorio base donde se guardarán los resultados.

    Flujo de ejecución:
        1. Define los directorios de salida (HTML / CSV).
        2. Crea una sesión HTTP aislada para este período.
        3. Accede a la página intermedia de eeff Fondo.
        4. Recorre las pestañas del HTML para encontrar los cuadros.
        5. Descarga y guarda cada cuadro usando utilidades comunes.
    """
    html_dir = os.path.join(base_dir, "html", periodo)
    csv_dir = os.path.join(base_dir, "csv", periodo)

    session = crear_sesion()

    # URL intermedia específica para eeff Fondo
    #url_intermedia = (
    #    f"{BASE_URL}/apps/loadEstadisticas/loadFecuFondo.php"
    #    f"?menu=sci&menuN1=estfinfp&menuN2=NOID"
    #    f"&orden=30&periodo={periodo}&ext=.php"
    #)

    url_intermedia = (
        f"{BASE_URL}/apps/loadEstadisticas/loadFecuFondo.php"
        f"?menu=sci&menuN1=estfinfp&menuN2=NOID"
        f"&orden=30&periodo={periodo}&ext=.php"
)

    response = session.get(url_intermedia, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # En eeff los links están distribuidos en pestañas (div.tab-pane)
    links: list[str] = []
    for tab in soup.select('div.tab-pane[id^="idu_"]'):
        for a in tab.select('a[href*="loadCuadroFecuFondo.php"]'):
            href = a.get("href")
            if "tipo=html" in href:
                links.append(urljoin(url_intermedia, href))

    descargar_y_guardar_cuadros(
        session=session,
        links=links,
        html_dir=html_dir,
        csv_dir=csv_dir,
        logger=logger,
        contexto=f"eeff {periodo}",
    )


# ============================================================
# API PÚBLICA – RANGO DE AÑOS
# ============================================================
def descargar_eeff_rango(
    desde_anio: int,
    hasta_anio: int,
    base_dir: str = DEFAULT_EEFF_DIR,
) -> None:
    """
    Descarga estados eeff Fondo para todos los meses de un rango de años.

    Args:
        desde_anio (int): Año inicial (inclusive).
        hasta_anio (int): Año final (inclusive).
        base_dir (str): Directorio base de salida.

    Nota:
        Wrapper explícito para mantener simetría con Carteras.
    """
    for anio in range(desde_anio, hasta_anio + 1):
        for mes in range(1, 13):
            periodo = f"{anio}{mes:02d}"
            descargar_eeff(periodo, base_dir=base_dir)
