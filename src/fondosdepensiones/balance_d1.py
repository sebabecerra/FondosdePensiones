"""
Descarga de Balance D1 desde el sitio de la
Superintendencia de Pensiones (Chile).

Este módulo replica EXACTAMENTE el comportamiento del botón
"Buscar" del formulario D1 disponible en:

https://www.spensiones.cl/apps/formularioD1/obtenerD1.php

Características de la fuente:
- Periodicidad: mensual (YYYYMM)
- Entrega: archivo ZIP oficial
- Contenido: archivo CSV o TXT (normalmente con separador ';')
- No existe navegación HTML de cuadros

Responsabilidades del módulo:
- Construir correctamente la request HTTP equivalente al botón "Buscar"
- Descargar el ZIP oficial del Balance D1
- Guardar el ZIP como respaldo binario
- Extraer el archivo CSV/TXT contenido y guardarlo explícitamente

Decisiones de diseño:
- No imprime directamente (usa logging)
- No genera rangos de períodos (eso lo hace el CLI)
- No transforma el CSV/TXT (solo extracción)
- Mantiene estructura de carpetas coherente con el proyecto

Estructura de salida:
data/balance_d1/{YYYY}/{MM}/
├── zip/
│   └── balance_d1_YYYYMM.zip
└── csv/
    └── balance_d1_YYYYMM.csv   (o .txt según fuente)

API pública:
- descargar_balance_d1(periodo, base_dir)
- descargar_balance_d1_rango(desde_anio, hasta_anio, base_dir)
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from .config import BASE_URL, DATA_DIR
from .session import crear_sesion
from .logger import configurar_logger

logger = configurar_logger(__name__)

# ------------------------------------------------------------
# Directorio por defecto
# ------------------------------------------------------------
DEFAULT_BALANCE_D1_DIR = DATA_DIR / "balance_d1"

# ============================================================
# API PÚBLICA – PERÍODO ÚNICO
# ============================================================
def descargar_balance_d1(
    periodo: str,
    base_dir: Path = DEFAULT_BALANCE_D1_DIR,
) -> None:
    """
    Descarga el Balance D1 para un período mensual específico.

    Args:
        periodo (str): Período en formato YYYYMM (ej: "202505").
        base_dir (Path): Directorio base de salida.

    Flujo de ejecución:
        1. Valida el período solicitado
        2. Replica la request del botón "Buscar"
        3. Descarga el ZIP oficial
        4. Guarda el ZIP como respaldo
        5. Extrae el archivo CSV/TXT contenido
    """
    # -------------------------
    # Validación básica
    # -------------------------
    anio = periodo[:4]
    
    base_dir = Path(base_dir)
    zip_dir = base_dir / anio / "zip"
    csv_dir = base_dir / anio / "csv"

    if len(periodo) != 6 or not periodo.isdigit():
        raise ValueError("periodo debe tener formato YYYYMM")

    contexto = f"BALANCE_D1 {periodo}"
    logger.info("[%s] Inicio descarga", contexto)

    # -------------------------
    # Directorios de salida
    # -------------------------
    anio = periodo[:4]

    base_dir = Path(base_dir)
    zip_dir = base_dir / anio / "zip"
    csv_dir = base_dir / anio / "csv"

    zip_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)

    zip_path = zip_dir / f"balance_d1_{periodo}.zip"

    # -------------------------
    # Sesión HTTP
    # -------------------------
    session = crear_sesion()
    session.headers.update({
        "Referer": f"{BASE_URL}/apps/formularioD1/obtenerD1.php",
        "Accept": "*/*",
    })

    url = (
        f"{BASE_URL}/apps/formularioD1/"
        f"downloadFile_balance.php"
    )

    params = {"periodo": periodo}

    logger.info("[%s] GET %s", contexto, url)

    resp = session.get(url, params=params, timeout=30)

    logger.info(
        "[%s] Status %s | Content-Type %s",
        contexto,
        resp.status_code,
        resp.headers.get("Content-Type"),
    )

    if resp.status_code != 200:
        logger.warning("[%s] Descarga fallida", contexto)
        return

    if "zip" not in resp.headers.get("Content-Type", "").lower():
        logger.warning("[%s] Respuesta no es ZIP", contexto)
        return

    # -------------------------
    # Guardar ZIP
    # -------------------------
    with open(zip_path, "wb") as f:
        f.write(resp.content)

    logger.info("[%s] ZIP guardado: %s", contexto, zip_path)

    # -------------------------
    # Extraer contenido del ZIP
    # -------------------------
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        for member in z.namelist():
            target = csv_dir / member

            logger.info(
                "[%s] Extrayendo archivo: %s",
                contexto,
                member,
            )

            with z.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())

    logger.info("[%s] Descarga finalizada", contexto)


# ============================================================
# API PÚBLICA – RANGO DE AÑOS
# ============================================================
def descargar_balance_d1_rango(
    desde_anio: int,
    hasta_anio: int,
    base_dir: Path = DEFAULT_BALANCE_D1_DIR,
) -> None:
    """
    Descarga Balance D1 para todos los meses de un rango de años.

    Args:
        desde_anio (int): Año inicial (inclusive).
        hasta_anio (int): Año final (inclusive).
        base_dir (Path): Directorio base de salida.

    Nota:
        Esta función es un wrapper de conveniencia.
        La lógica real vive en `descargar_balance_d1`.
    """
    for anio in range(desde_anio, hasta_anio + 1):
        for mes in range(1, 13):
            periodo = f"{anio}{mes:02d}"
            descargar_balance_d1(periodo, base_dir=base_dir)