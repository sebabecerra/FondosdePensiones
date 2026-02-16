"""Descarga concurrente de Carteras Agregadas de Fondos de Pensiones.

Este módulo implementa la lógica de negocio para obtener la composición 
agregada de carteras mensuales. Utiliza un patrón de inyección de parámetros 
para escalar el rendimiento mediante concurrencia multi-hilo.

API pública:
    - descargar_carteras: Obtiene los cuadros de un periodo mensual único.
    - descargar_carteras_rango: Orquesta descargas para múltiples años.
"""

from __future__ import annotations

import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import Any, List

from .config import BASE_URL, DEFAULT_CARTERAS_INVERSIONES_AGREGADA_DIR
from .session import crear_sesion
from .cuadros_utils import descargar_y_guardar_cuadros
from .logger import configurar_logger

# Configuración de logger profesional
logger = configurar_logger(__name__)


def descargar_carteras(
    periodo: str,
    base_dir: str = DEFAULT_CARTERAS_INVERSIONES_AGREGADA_DIR,
    **kwargs: Any,
) -> None:
    """Descarga de forma paralela todas las carteras de un periodo mensual.

    Accede al índice mensual de la Superintendencia, identifica los cuadros
    disponibles y delega su descarga a un pool de hilos concurrente.

    Args:
        periodo: Identificador temporal en formato 'YYYYMM'.
        base_dir: Directorio raíz de almacenamiento.
        **kwargs: Saco de configuración inyectado desde el CLI. 
            Contiene 'max_workers' para el motor de hilos.

    Raises:
        requests.exceptions.HTTPError: Si el servidor remoto no es accesible.
    """
    # CONEXIÓN TÉCNICA: Extraemos 'max_workers' del saco inyectado por el CLI.
    # Si por alguna razón no viene, caemos a un default seguro de 5.
    workers = kwargs.get("max_workers", 5)

    # Definición de la jerarquía de almacenamiento cronológico (Año/Mes)
    anio = periodo[:4]
    html_dir = os.path.join(base_dir,"html", anio, periodo)
    csv_dir = os.path.join(base_dir, "csv", anio, periodo)

    # Sesión con soporte Keep-Alive para optimizar la latencia en hilos
    session = crear_sesion()

    # URL que actúa como gateway para listar los cuadros del mes
    url_intermedia = (
        f"{BASE_URL}/apps/loadCarteras/loadCarAgr.php"
        f"?menu=sci&menuN1=estfinfp&menuN2=NOID"
        f"&orden=20&periodo={periodo}&ext=.php"
    )

    try:
        response = session.get(url_intermedia, timeout=30)
        response.raise_for_status()
    except Exception as e:
        logger.error("[CARTERAS %s] Error al acceder a la página intermedia: %s", periodo, e)
        return

    # Extracción de links filtrando solo los generadores de tablas HTML
    soup = BeautifulSoup(response.text, "html.parser")
    links: List[str] = [
        urljoin(BASE_URL, a["href"])
        for a in soup.find_all("a", title="Html", href=True)
        if "genera_xsl_v2.0.php" in a["href"]
    ]

    if not links:
        logger.warning("[CARTERAS %s] No se detectaron cuadros para este periodo.", periodo)
        return

    # DESPACHO CONCURRENTE: Aquí pasamos finalmente el 'workers' real al motor de cuadros.
    # Esto hará que el log de cuadros_utils diga '(8 workers)' si así se pidió.
    descargar_y_guardar_cuadros(
        session=session,
        links=links,
        html_dir=html_dir,
        csv_dir=csv_dir,
        logger=logger,
        contexto=f"CARTERAS {periodo}",
        max_workers=workers
    )


def descargar_carteras_rango(
    desde_anio: int,
    hasta_anio: int,
    base_dir: str = DEFAULT_CARTERAS_INVERSIONES_AGREGADA_DIR,
    **kwargs: Any,
) -> None:
    """Orquesta la descarga cronológica para un rango multi-anual.

    Args:
        desde_anio: Año inicial del rango.
        hasta_anio: Año final del rango.
        base_dir: Directorio raíz de almacenamiento.
        **kwargs: Saco de configuración para propagar a los hilos.
    """
    for anio in range(desde_anio, hasta_anio + 1):
        for mes in range(1, 13):
            periodo = f"{anio}{mes:02d}"
            # Propagamos el saco de configuración completo a cada llamada mensual
            descargar_carteras(periodo, base_dir=base_dir, **kwargs)