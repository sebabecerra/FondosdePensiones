"""Módulo de utilidades concurrentes para la persistencia de cuadros financieros.

Este módulo centraliza la lógica de descarga multi-hilo para los cuadros de
Carteras de Inversión y Estados Financieros (EEFF). Implementa un motor de 
concurrencia basado en hilos (threads) optimizado para tareas limitadas por 
red (I/O-bound).

Principios de Ingeniería aplicados:
    - Resiliencia: Reintentos automáticos con bloqueos preventivos (backoff).
    - Seguridad de Hilos: Uso de requests.Session para reutilizar conexiones TCP.
    - Validación Estructural: Rechazo de payloads HTML incompletos o corruptos.
    - Observabilidad: Telemetría básica vía logging para monitorear el progreso del pool.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, Any

from .html_utils import decode_html, extraer_titulo, limpiar_nombre
from .io_utils import guardar_html_y_csv


def _html_es_valido(html: str) -> bool:
    """Realiza una inspección estructural mínima del payload HTML recibido.

    Evita que el pipeline de procesamiento (Pandas) falle al intentar parsear 
    respuestas vacías o truncadas enviadas por el servidor de SPensiones.

    Args:
        html: Contenido HTML decodificado.

    Returns:
        bool: True si el HTML contiene etiquetas críticas (table, tr), False si no.
    """
    if not html or len(html) < 500:
        return False
    
    html_lower = html.lower()
    return "<table" in html_lower and "<tr" in html_lower


def descargar_y_guardar_cuadros(
    *,
    session: Any,
    links: Iterable[str],
    html_dir: str,
    csv_dir: str,
    logger: Any,
    contexto: str,
    max_workers: int = 5,
) -> None:
    """Orquesta la descarga concurrente de una lista de cuadros HTML.

    Implementa el patrón Master-Worker utilizando un ThreadPoolExecutor. Cada hilo
    se encarga de la descarga, validación y persistencia de un cuadro individual.

    Args:
        session: Instancia de requests.Session (Thread-safe para peticiones GET).
        links: Colección de URLs de los cuadros a descargar.
        html_dir: Ruta absoluta para el almacenamiento de archivos HTML originales.
        csv_dir: Ruta absoluta para el almacenamiento de archivos CSV procesados.
        logger: Instancia del logger del módulo llamador para trazabilidad.
        contexto: Etiqueta descriptiva del proceso (ej. 'CARTERAS 202401').
        max_workers: Límite de hilos simultáneos para balancear velocidad y cortesía.

    Note:
        La reutilización de la 'session' es crítica para el rendimiento, ya que
        permite el uso de Keep-Alive, evitando el apretón de manos (handshake) 
        TCP/SSL en cada petición.
    """
    # Convertimos a lista para conocer el total y permitir indexación
    links_list = list(links)
    total_cuadros = len(links_list)

    def _worker(index: int, url: str) -> bool:
        """Tarea atómica ejecutada por un hilo del pool.

        Args:
            index: Índice del cuadro para nomenclatura por defecto.
            url: URL del recurso remoto.

        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        max_reintentos = 3
        html_final = None

        # Ciclo de reintentos con lógica de espera
        for intento in range(1, max_reintentos + 1):
            try:
                # Timeout generoso para evitar bloqueos por latencia del servidor
                response = session.get(url, timeout=45)
                response.raise_for_status()

                # Decodificación robusta manejando caracteres especiales (Â, \xa0)
                html_raw = decode_html(response).replace("\xa0", " ").replace("Â", "")

                if _html_es_valido(html_raw):
                    html_final = html_raw
                    break
                
                logger.warning(
                    "[%s] Payload inválido en cuadro %d/%d (Intento %d)", 
                    contexto, index, total_cuadros, intento
                )
            except Exception as e:
                logger.warning(
                    "[%s] Error de red en cuadro %d (Intento %d): %s", 
                    contexto, index, intento, e
                )
            
            # Tiempo de cortesía entre reintentos para no estresar el endpoint
            time.sleep(1.5)

        if not html_final:
            logger.error("[%s] Cuadro %d omitido tras fallar reintentos.", contexto, index)
            return False

        # Persistencia tras validación exitosa
        titulo = extraer_titulo(html_final, fallback=f"cuadro_{index:02d}")
        nombre_normalizado = limpiar_nombre(titulo) or f"cuadro_{index:02d}"

        guardar_html_y_csv(
            html=html_final,
            nombre=nombre_normalizado,
            html_dir=html_dir,
            csv_dir=csv_dir,
        )
        return True

    # --- Orquestación del Pool de Hilos ---
    logger.info(
        "[%s] Iniciando descarga concurrente de %d cuadros (%s workers)", 
        contexto, total_cuadros, max_workers
    )
    
    exitos = 0
    # Context Manager asegura el cierre limpio de los hilos al finalizar
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Despacho de tareas (Futures)
        tareas = {
            executor.submit(_worker, i, link): link 
            for i, link in enumerate(links_list, start=1)
        }

        # Procesamiento a medida que se completan (no importa el orden de llegada)
        for future in as_completed(tareas):
            try:
                if future.result():
                    exitos += 1
            except Exception as e:
                logger.error("[%s] Excepción no controlada en hilo: %s", contexto, e)

    logger.info(
        "[%s] Proceso finalizado. Cobertura: %d/%d cuadros.", 
        contexto, exitos, total_cuadros
    )