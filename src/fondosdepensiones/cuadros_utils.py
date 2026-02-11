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
- eeff.py

────────────────────────────────────────────────────────────────────
PROBLEMA QUE RESUELVE ESTA VERSIÓN
────────────────────────────────────────────────────────────────────
En ejecuciones largas (muchos períodos / muchos cuadros), el servidor
de SPensiones ocasionalmente responde con HTML:

- vacío
- truncado
- sin <table>
- sin filas <tr>

Eso provoca fallas intermitentes en pandas.read_html(), típicamente:
    lxml.etree.XMLSyntaxError: no text parsed from document

IMPORTANTE:
- El recurso SÍ existe (al reintentar manualmente funciona).
- El problema es de transporte / timing, NO de lógica.

Esta versión implementa:
✔ validación estructural del HTML
✔ reintentos automáticos
✔ bloqueo explícito del pipeline si el HTML es inválido
✔ cero CSV vacíos
"""

from typing import Iterable
import time

from .html_utils import decode_html, extraer_titulo, limpiar_nombre
from .io_utils import guardar_html_y_csv


# ============================================================
# VALIDACIÓN DEFENSIVA DE HTML
# ============================================================
def _html_es_valido(html: str) -> bool:
    """
    Determina si un HTML es estructuralmente apto para ser parseado.

    Reglas mínimas (todas deben cumplirse):
    - El HTML no es None ni vacío
    - Tiene un tamaño mínimo razonable
    - Contiene al menos una <table>
    - Contiene al menos una fila <tr>

    Esta validación evita pasar basura a pandas.read_html().
    """
    if not html:
        return False

    # HTML demasiado pequeño suele ser error / respuesta incompleta
    if len(html) < 500:
        return False

    html_lower = html.lower()

    if "<table" not in html_lower:
        return False

    if "<tr" not in html_lower:
        return False

    return True


# ============================================================
# API PRINCIPAL
# ============================================================
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

    DIFERENCIA CLAVE CON LA VERSIÓN ANTERIOR
    ---------------------------------------
    Esta función SOLO continúa el pipeline cuando el HTML descargado
    es estructuralmente válido.

    Si el HTML llega incompleto:
    - reintenta automáticamente
    - NO genera CSV basura
    - NO detiene el proceso completo
    - omite solo el cuadro fallido

    Args:
        session: requests.Session activa (gestionada por el módulo llamador).
        links: iterable de URLs de cuadros HTML.
        html_dir: directorio de salida para HTML.
        csv_dir: directorio de salida para CSV.
        logger: logger del módulo llamador.
        contexto: texto descriptivo para logging
                  (ej: 'CARTERAS 202401', 'EEFF 202312').
    """

    # Convertimos a lista explícita porque:
    # - necesitamos len()
    # - links puede venir como generador
    links = list(links)
    total = len(links)

    # Parámetros de robustez (ajustables)
    MAX_REINTENTOS = 3
    SLEEP_ENTRE_REINTENTOS = 1.5  # segundos

    for i, link in enumerate(links, start=1):
        logger.info("[%s] Descargando cuadro %d/%d", contexto, i, total)

        html_base = None

        # ----------------------------------------------------
        # REINTENTOS CONTROLADOS
        # ----------------------------------------------------
        for intento in range(1, MAX_REINTENTOS + 1):
            try:
                resp = session.get(link, timeout=60)
                resp.raise_for_status()

                html_tmp = (
                    decode_html(resp)
                    .replace("\xa0", " ")
                    .replace("Â", "")
                )

                # Validación estructural CRÍTICA
                if _html_es_valido(html_tmp):
                    html_base = html_tmp
                    break

                logger.warning(
                    "[%s] HTML inválido (cuadro %d/%d). "
                    "Reintento %d/%d",
                    contexto,
                    i,
                    total,
                    intento,
                    MAX_REINTENTOS,
                )

            except Exception as e:
                logger.warning(
                    "[%s] Error descargando cuadro %d/%d "
                    "(intento %d/%d): %s",
                    contexto,
                    i,
                    total,
                    intento,
                    MAX_REINTENTOS,
                    e,
                )

            # Espera breve para evitar golpear el servidor
            time.sleep(SLEEP_ENTRE_REINTENTOS)

        # ----------------------------------------------------
        # SI TRAS REINTENTOS EL HTML SIGUE MALO → SE OMITE
        # ----------------------------------------------------
        if html_base is None:
            logger.error(
                "[%s] HTML NO válido tras %d intentos. "
                "Cuadro %d/%d omitido.",
                contexto,
                MAX_REINTENTOS,
                i,
                total,
            )
            continue

        # ----------------------------------------------------
        # A PARTIR DE AQUÍ EL HTML ES CONFIABLE
        # ----------------------------------------------------
        titulo = extraer_titulo(
            html_base,
            fallback=f"cuadro_{i:02d}"
        )

        nombre = limpiar_nombre(titulo) or f"cuadro_{i:02d}"

        guardar_html_y_csv(
            html=html_base,
            nombre=nombre,
            html_dir=html_dir,
            csv_dir=csv_dir,
        )