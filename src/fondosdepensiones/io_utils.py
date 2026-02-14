"""
Utilidades de entrada/salida (HTML y CSV).

Pipeline robusto SPensiones:

1. Preservar primera fila como nombres de variables.
2. Limpiar nombres de columnas (\n, \xa0, espacios).
3. Transformación numérica Chile:
   1.234,56 → 1234.56
4. Conversión segura de columnas numéricas (pandas 2.x).
5. CSV compatible con Excel Chile (utf-8-sig).
"""

import os
from io import StringIO
import pandas as pd
from .logger import configurar_logger

logger = configurar_logger(__name__)


def guardar_html_y_csv(
    html: str,
    nombre: str,
    html_dir: str,
    csv_dir: str
) -> None:

    # ----------------------------------
    # 1. Crear carpetas de salida
    # ----------------------------------
    os.makedirs(html_dir, exist_ok=True)
    os.makedirs(csv_dir, exist_ok=True)

    # ----------------------------------
    # 2. Guardar HTML original
    # ----------------------------------
    html_path = os.path.join(html_dir, f"{nombre}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    try:
        # ----------------------------------
        # 3. Transformación numérica Chile
        # (miles "." → nada)
        # (decimal "," → ".")
        # ----------------------------------
        html_transformado = html.replace(".", "").replace(",", ".")

        # ----------------------------------
        # 4. Leer tabla HTML
        # header=0 → primera fila = nombres
        # ----------------------------------
        tablas = pd.read_html(
            StringIO(html_transformado),
            header=0
        )

        if not tablas:
            logger.warning("[%s] No se detectaron tablas.", nombre)
            return

        df = tablas[0]

        # ----------------------------------
        # 5. Limpieza de nombres columnas
        # ----------------------------------
        df.columns = (
            df.columns
            .astype(str)
            .str.replace('\n', ' ', regex=False)
            .str.replace('\xa0', ' ', regex=False)
            .str.strip()
            .str.lower()
            .str.replace('%', 'pct', regex=False)
            .str.replace(' ', '_', regex=False)
        )

        # ----------------------------------
        # 6. Conversión numérica segura
        # pandas 2.x compatible
        # ----------------------------------
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # ----------------------------------
        # 7. Guardar CSV final
        # utf-8-sig → Excel Chile OK
        # ----------------------------------
        csv_path = os.path.join(csv_dir, f"{nombre}.csv")

        df.to_csv(
            csv_path,
            index=False,
            encoding="utf-8-sig"
        )

        logger.debug("[%s] CSV generado correctamente.", nombre)

    except Exception as e:
        logger.error(
            "[%s] Error crítico al procesar tabla: %s",
            nombre,
            e
        )