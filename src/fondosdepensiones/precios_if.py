"""Módulo de descarga de Precios de Instrumentos Financieros (IF).

Este módulo gestiona la descarga de archivos ZIP diarios oficiales desde la
Superintendencia de Pensiones. Aplica optimizaciones de red saltando días 
no hábiles (fines de semana) donde no existe publicación de precios.

Estructura de salida:
    data/precios_if/{anio}/{mes}/
    ├── zip/   → Respaldos binarios (.zip)
    └── txt/   → Datos extraídos (.txt)
"""

from __future__ import annotations

import io
import zipfile
from datetime import date, timedelta
from pathlib import Path

from .config import BASE_URL, DEFAULT_PRECIOS_IF_DIR
from .session import crear_sesion
from .logger import configurar_logger

logger = configurar_logger(__name__)

# Mapeo de meses según estándar de URL de SPensiones
MESES_MAP = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr",
    5: "may", 6: "jun", 7: "jul", 8: "ago",
    9: "sep", 10: "oct", 11: "nov", 12: "dic",
}


def descargar_precios_if_anio(anio: int) -> None:
    """Descarga el dataset completo de Precios IF para un año específico.

    Itera día por día, validando si es un día de mercado (Lunes-Viernes)
    antes de intentar la descarga.

    Args:
        anio: Año calendario a procesar (ej. 2024).
    """
    contexto = f"PRECIOS_IF {anio}"
    logger.info("[%s] Iniciando ciclo de descarga anual", contexto)

    session = crear_sesion()
    
    # Rango temporal
    fecha_actual = date(anio, 1, 1)
    fecha_fin = date(anio, 12, 31)

    while fecha_actual <= fecha_fin:
        # ---------------------------------------------------------------------
        # OPTIMIZACIÓN: Validación de Fin de Semana (L=0, ..., S=5, D=6)
        # ---------------------------------------------------------------------
        if fecha_actual.weekday() >= 5:
            # Saltamos Sábado y Domingo silenciosamente para no saturar el log
            fecha_actual += timedelta(days=1)
            continue

        mes_str = MESES_MAP[fecha_actual.month]
        zip_name = f"p{fecha_actual:%Y%m%d}.zip"

        # Construcción de URL determinística
        url = (
            f"{BASE_URL}/apps/GetFile.php"
            f"?id=006&namefile={anio}/{mes_str}/{zip_name}"
        )

        try:
            response = session.get(url, timeout=20)

            if response.status_code == 200:
                logger.info("[%s] Descargando: %s", contexto, zip_name)
                _procesar_archivo_zip(fecha_actual, zip_name, response.content)
            elif response.status_code == 404:
                # Los feriados legales también caen aquí
                logger.debug("[%s] Archivo no encontrado (posible feriado): %s", contexto, zip_name)
            else:
                logger.warning("[%s] Error inesperado %s en %s", contexto, response.status_code, zip_name)

        except Exception as e:
            logger.error("[%s] Error de conexión en fecha %s: %s", contexto, fecha_actual, e)

        fecha_actual += timedelta(days=1)

    logger.info("[%s] Ciclo anual finalizado", contexto)


def _procesar_archivo_zip(fecha: date, nombre_zip: str, contenido: bytes) -> None:
    """Encapsula la lógica de persistencia y extracción de archivos.

    Args:
        fecha: Objeto date correspondiente al archivo.
        nombre_zip: Nombre del archivo ZIP en el servidor.
        contenido: Payload binario del archivo.
    """
    # Definición de rutas siguiendo la jerarquía del proyecto
    base_path = Path(DEFAULT_PRECIOS_IF_DIR) / str(fecha.year) / f"{fecha.month:02d}"
    zip_dir = base_path / "zip"
    txt_dir = base_path / "txt"

    zip_dir.mkdir(parents=True, exist_ok=True)
    txt_dir.mkdir(parents=True, exist_ok=True)

    # 1. Persistencia del ZIP (Respaldo)
    zip_path = zip_dir / nombre_zip
    zip_path.write_bytes(contenido)

    # 2. Extracción de contenidos (Data usable)
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            for member in z.namelist():
                # En Google, evitamos extraer archivos fuera del directorio (ZipSlip)
                if member.startswith("/") or ".." in member:
                    continue
                
                target_path = txt_dir / member
                target_path.parent.mkdir(parents=True, exist_ok=True)

                with z.open(member) as src, open(target_path, "wb") as dst:
                    dst.write(src.read())
    except zipfile.BadZipFile:
        logger.error("El archivo %s está corrupto o no es un ZIP válido", nombre_zip)