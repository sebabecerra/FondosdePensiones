"""
Descarga de Valores Cuota de Fondos de Pensiones (Chile).

Este módulo implementa la descarga directa de valores cuota
utilizando el endpoint oficial expuesto por SPensiones.

Características:
- No usa scraping HTML.
- Consume directamente el endpoint vcfAFPxls.php.
- Descarga archivos CSV/XLS "falso" oficiales.
- Guarda resultados en data/Valores_Cuota/.
- Compatible con rangos de años.

API pública:
- descargar_valores_cuota(desde_anio, hasta_anio, base_dir)
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from .config import DEFAULT_VALORES_CUOTA_DIR
from .session import crear_sesion
from .logger import configurar_logger

logger = configurar_logger(__name__)

# Endpoint correcto (relativo a valoresCuotaFondo)
VCF_XLS_ENDPOINT = (
    "https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFPxls.php"
)


# ============================================================
# API PÚBLICA
# ============================================================
def descargar_valores_cuota(
    desde_anio: int,
    hasta_anio: int,
    *,
    tipo_fondo: str = "C",
    base_dir: Union[str, Path] = DEFAULT_VALORES_CUOTA_DIR,
) -> None:
    """
    Descarga Valores Cuota para un rango de años.

    Args:
        desde_anio (int): Año inicial (inclusive).
        hasta_anio (int): Año final (inclusive).
        tipo_fondo (str): Tipo de fondo (A, B, C, D, E). Default: "C".
        base_dir (str | Path): Directorio base de salida.

    Flujo:
        1. Construye parámetros oficiales del endpoint.
        2. Descarga el archivo CSV/XLS.
        3. Guarda el archivo en data/Valores_Cuota/.
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    session = crear_sesion()

    params = {
        "aaaaini": desde_anio,
        "aaaafin": hasta_anio,
        "tf": tipo_fondo,
        # Fecha de confección: SPensiones no valida estrictamente,
        # se deja fija y consistente
        "fecconf": "20260131",
    }

    logger.info(
        "[VALORES_CUOTA] Descargando %s-%s (Fondo %s)",
        desde_anio,
        hasta_anio,
        tipo_fondo,
    )

    response = session.get(VCF_XLS_ENDPOINT, params=params, timeout=60)
    response.raise_for_status()

    output_file = base_dir / f"valores_cuota_{tipo_fondo}_{desde_anio}_{hasta_anio}.csv"

    with open(output_file, "wb") as f:
        f.write(response.content)

    logger.info(
        "[VALORES_CUOTA] Archivo guardado: %s",
        output_file,
    )
