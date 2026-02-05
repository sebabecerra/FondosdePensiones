"""
Utilidades de entrada/salida (HTML y CSV).
"""

import os
from io import StringIO
import pandas as pd


def guardar_html_y_csv(
    html: str,
    nombre: str,
    html_dir: str,
    csv_dir: str
) -> None:
    """
    Guarda un HTML y extrae su primera tabla como CSV.

    Args:
        html (str): HTML completo ya decodificado.
        nombre (str): nombre base del archivo (sin extensión).
        html_dir (str): directorio destino HTML.
        csv_dir (str): directorio destino CSV.
    """
    os.makedirs(html_dir, exist_ok=True)
    os.makedirs(csv_dir, exist_ok=True)

    # Guardar HTML
    html_path = os.path.join(html_dir, f"{nombre}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Convertir a CSV
    html_tablas = html.replace(".", "").replace(",", ".")
    tablas = pd.read_html(StringIO(html_tablas))

    if not tablas:
        return

    csv_path = os.path.join(csv_dir, f"{nombre}.csv")
    tablas[0].to_csv(csv_path, index=False)
