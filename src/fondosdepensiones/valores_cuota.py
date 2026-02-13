"""Módulo de descarga de Valores Cuota de Fondos de Pensiones (Chile).

Este módulo gestiona la obtención de series históricas de valores cuota y 
patrimonio desde el portal oficial de SPensiones. A diferencia de otros 
módulos, este consume un endpoint que genera archivos en formato XLS 
(HTML tabulado) que tratamos como archivos planos para su posterior análisis.

Estructura de Almacenamiento:
    data/Valores_Cuota/{AAAA}/valores_cuota_{FONDO}_{AAAA}.csv

Regla de Negocio:
    - Los archivos se particionan por año para asegurar la escalabilidad.
    - Se utiliza el endpoint 'vcfAFPxls.php' para evitar el scraping complejo.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Union

from .config import DEFAULT_VALORES_CUOTA_DIR
from .session import crear_sesion
from .logger import configurar_logger

# Configuración de Logging con el namespace del módulo
logger = configurar_logger(__name__)

# Endpoint oficial para exportación masiva de valores cuota
VCF_XLS_ENDPOINT = (
    "https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFPxls.php"
)


def descargar_valores_cuota(
    desde_anio: int,
    hasta_anio: int,
    *,
    tipo_fondo: str = "C",
    base_dir: Union[str, Path] = DEFAULT_VALORES_CUOTA_DIR,
) -> None:
    """Descarga y organiza los Valores Cuota en una jerarquía cronológica.

    Itera sobre el rango de años solicitado, realizando una petición por cada 
    año para mantener la consistencia en el almacenamiento particionado.

    Args:
        desde_anio: Año inicial del periodo (ej. 2020).
        hasta_anio: Año final del periodo (inclusive, ej. 2024).
        tipo_fondo: Letra del fondo de pensiones ('A', 'B', 'C', 'D', 'E').
            Por defecto es 'C'.
        base_dir: Directorio raíz donde se creará la jerarquía de carpetas.
            Viene predefinido desde config.py.

    Raises:
        requests.exceptions.HTTPError: Si el servidor de SPensiones no responde 
            con un código 200.
        OSError: Si existen problemas de permisos al crear directorios o archivos.

    Flow:
        1. Inicializa una sesión HTTP persistente.
        2. Crea subdirectorios por cada año en el rango.
        3. Consume el endpoint binario de la Superintendencia.
        4. Persiste el contenido en disco con nomenclatura normalizada.
    """
    base_dir = Path(base_dir)
    session = crear_sesion()

    # Particionamiento cronológico: un archivo por cada año calendario
    for anio in range(desde_anio, hasta_anio + 1):
        
        # Definición de ruta siguiendo el estándar del proyecto: Dataset/Año/
        anio_dir = base_dir / str(anio)
        anio_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "[VALORES_CUOTA] Iniciando descarga Año %s (Fondo %s)", 
            anio, tipo_fondo
        )

        # Parámetros oficiales del formulario de SPensiones
        # 'fecconf' es un parámetro de control interno del servidor
        params = {
            "aaaaini": anio,
            "aaaafin": anio,
            "tf": tipo_fondo,
            "fecconf": "20260131",
        }

        try:
            # Petición con timeout extendido debido al procesamiento interno del servidor
            response = session.get(VCF_XLS_ENDPOINT, params=params, timeout=60)
            response.raise_for_status()

            # Nomenclatura técnica: valores_cuota_{FONDO}_{AÑO}.csv
            output_file = anio_dir / f"valores_cuota_{tipo_fondo}_{anio}.csv"

            # Guardado en binario para preservar la integridad del stream XLS/CSV
            with open(output_file, "wb") as f:
                f.write(response.content)

            logger.info("[VALORES_CUOTA] Persistencia exitosa: %s", output_file)

        except Exception as e:
            # Log de error específico por año para no interrumpir el rango completo
            logger.error(
                "[VALORES_CUOTA] Fallo crítico en el año %s: %s", 
                anio, e
            )
            continue

    logger.info("[VALORES_CUOTA] Proceso de rango finalizado exitosamente.")