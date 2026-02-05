"""
Utilidades comunes para descarga y persistencia de cuadros HTML/CSV.

Este módulo centraliza la lógica repetida de:
- Descargar HTML desde una lista de links
- Decodificar HTML
- Extraer títulos
- Normalizar nombres de archivo
- Guardar HTML y CSV

Debe ser usado por:
- carteras.py
- fecu.py
"""

from typing import Iterable
from .html_utils import decode_html, extraer_titulo, limpiar_nombre
from .io_utils import guardar_html_y_csv


def descargar_y_guardar_cuadros(
    *,
    session,
    links: Iterable[str],
    html_dir: str,
    csv_dir: str,
    logger,
    contexto: str,
) -> None:
    """
    Descarga una lista de cuadros HTML y guarda HTML + CSV.

    Args:
        session: requests.Session activa.
        links: iterable de URLs de cuadros HTML.
        html_dir: directorio de salida para HTML.
        csv_dir: directorio de salida para CSV.
        logger: logger del módulo llamador.
        contexto: texto descriptivo para logging
                  (ej: 'CARTERAS 202401', 'FECU 202312').

    Flujo:
        - Itera sobre cada link
        - Descarga HTML
        - Decodifica contenido
        - Extrae título desde <h3>
        - Normaliza nombre
        - Guarda HTML original y CSV normalizado
    """
    total = len(list(links))

    for i, link in enumerate(links, start=1):
        logger.info("[%s] Descargando cuadro %d/%d", contexto, i, total)

        resp = session.get(link, timeout=60)
        resp.raise_for_status()

        html_base = decode_html(resp).replace("\xa0", " ").replace("Â", "")
        titulo = extraer_titulo(html_base, fallback=f"cuadro_{i:02d}")
        nombre = limpiar_nombre(titulo) or f"cuadro_{i:02d}"

        guardar_html_y_csv(
            html=html_base,
            nombre=nombre,
            html_dir=html_dir,
            csv_dir=csv_dir,
        )
