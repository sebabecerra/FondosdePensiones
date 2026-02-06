"""
Descarga de Precios de Instrumentos Financieros (IF) desde SPensiones.

Este módulo:
- Descarga archivos ZIP diarios oficiales.
- Guarda los ZIP originales como respaldo.
- Extrae y guarda los archivos TXT contenidos.

Estructura de salida:
data/precios_if/{anio}/{mes}/
├── zip/   → ZIP diarios
└── txt/   → TXT extraídos

Nota:
- Dataset de frecuencia diaria.
- No existe índice HTML de archivos históricos.
- Se utiliza URL determinística por fecha.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import io
import zipfile

from .config import BASE_URL, DEFAULT_PRECIOS_IF_DIR
from .session import crear_sesion
from .logger import configurar_logger

logger = configurar_logger(__name__)

MESES = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr",
    5: "may", 6: "jun", 7: "jul", 8: "ago",
    9: "sep", 10: "oct", 11: "nov", 12: "dic",
}


def descargar_precios_if_anio(anio: int) -> None:
    """
    Descarga todos los Precios IF diarios para un año completo.

    Args:
        anio (int): Año a descargar (ej: 2025)

    Flujo:
        - Itera día por día.
        - Construye la URL oficial del ZIP.
        - Si existe (HTTP 200):
            * Guarda ZIP.
            * Extrae TXT.
    """
    contexto = f"PRECIOS_IF {anio}"
    logger.info("[%s] Inicio descarga", contexto)

    session = crear_sesion()

    fecha = date(anio, 1, 1)
    fin = date(anio, 12, 31)

    while fecha <= fin:
        mes_txt = MESES[fecha.month]
        zip_name = f"p{fecha:%Y%m%d}.zip"

        url = (
            f"{BASE_URL}/apps/GetFile.php"
            f"?id=006&namefile={anio}/{mes_txt}/{zip_name}"
        )

        r = session.get(url, timeout=30)

        if r.status_code == 200:
            logger.info("[%s] ZIP encontrado: %s", contexto, zip_name)

            # -------------------------
            # Directorios por mes
            # -------------------------
            base_dir = (
                Path(DEFAULT_PRECIOS_IF_DIR)
                / str(anio)
                / f"{fecha.month:02d}"
            )
            zip_dir = base_dir / "zip"
            txt_dir = base_dir / "txt"

            zip_dir.mkdir(parents=True, exist_ok=True)
            txt_dir.mkdir(parents=True, exist_ok=True)

            # -------------------------
            # Guardar ZIP
            # -------------------------
            zip_path = zip_dir / zip_name
            zip_path.write_bytes(r.content)

            # -------------------------
            # Extraer TXT
            # -------------------------
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                for member in z.namelist():
                    target = txt_dir / member
                    target.parent.mkdir(parents=True, exist_ok=True)

                    logger.info(
                        "[%s] Extrayendo %s", contexto, target.name
                    )

                    with z.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())

        fecha += timedelta(days=1)

    logger.info("[%s] Descarga finalizada", contexto)