"""
Descarga de Carteras Agregadas desde el sitio de la Superintendencia de Pensiones (Chile).

Este módulo implementa el flujo completo para obtener las Carteras Agregadas
de Fondos de Pensiones para un período mensual específico (YYYYMM).

Responsabilidades del módulo:
- Construir la URL intermedia de Carteras para un período dado.
- Extraer los links HTML de los cuadros disponibles.
- Delegar la descarga y persistencia de cada cuadro (HTML + CSV)
  a utilidades comunes reutilizables.

Decisiones de diseño:
- Este módulo NO imprime ni configura logging directamente.
- No genera rangos de períodos (eso se hace en capas superiores).
- Se apoya en `cuadros_utils` para evitar duplicación de lógica.
- Mantiene una API pública clara y estable.

API pública:
- descargar_carteras(periodo, base_dir)
- descargar_carteras_rango(desde_anio, hasta_anio, base_dir)
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



# ============================================================
# API PÚBLICA – PERÍODO ÚNICO
# ============================================================
def descargar_carteras(
    periodo: str,
    base_dir: str = DEFAULT_CARTERAS_INVERSIONES_AGREGADA_DIR,
) -> None:
    """
    Descarga las Carteras Agregadas para un período mensual específico.

    Args:
        periodo (str): Período en formato YYYYMM (ej: "202401").
        base_dir (str): Directorio base donde se guardarán los resultados.

    Flujo de ejecución:
        1. Define los directorios de salida (HTML / CSV).
        2. Crea una sesión HTTP aislada para este período.
        3. Accede a la página intermedia de Carteras.
        4. Extrae los links HTML de los cuadros disponibles.
        5. Descarga y guarda cada cuadro usando utilidades comunes.
    """
    # --- NUEVA LÓGICA DE DIRECTORIOS ---
    anio = periodo[:4]  # Extrae "2024" de "202401"

    # Directorios de salida organizados por período
    html_dir = os.path.join(base_dir, anio, "html", periodo)
    csv_dir = os.path.join(base_dir, anio, "csv", periodo)

    # Sesión HTTP dedicada (evita contaminación entre períodos)
    session = crear_sesion()

    # URL intermedia que lista los cuadros disponibles para el período
    url_intermedia = (
        f"{BASE_URL}/apps/loadCarteras/loadCarAgr.php"
        f"?menu=sci&menuN1=estfinfp&menuN2=NOID"
        f"&orden=20&periodo={periodo}&ext=.php"
    )

    response = session.get(url_intermedia, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Extracción explícita de links HTML válidos
    links = [
        urljoin(BASE_URL, a["href"])
        for a in soup.find_all("a", title="Html", href=True)
        if "genera_xsl_v2.0.php" in a["href"]
    ]

    # Descarga y persistencia delegada a utilidades comunes
    descargar_y_guardar_cuadros(
        session=session,
        links=links,
        html_dir=html_dir,
        csv_dir=csv_dir,
        logger=logger,
        contexto=f"CARTERAS {periodo}",
    )

# ============================================================
# API PÚBLICA – RANGO DE AÑOS
# ============================================================
def descargar_carteras_rango(
    desde_anio: int,
    hasta_anio: int,
    base_dir: str = DEFAULT_CARTERAS_INVERSIONES_AGREGADA_DIR,
) -> None:
    """
    Descarga Carteras Agregadas para todos los meses de un rango de años.

    Args:
        desde_anio (int): Año inicial (inclusive).
        hasta_anio (int): Año final (inclusive).
        base_dir (str): Directorio base de salida.

    Nota:
        Esta función es un wrapper de conveniencia.
        La lógica real por período vive en `descargar_carteras`.
    """
    for anio in range(desde_anio, hasta_anio + 1):
        for mes in range(1, 13):
            periodo = f"{anio}{mes:02d}"
            descargar_carteras(periodo, base_dir=base_dir)
