"""Módulo de descarga concurrente de Precios de Instrumentos Financieros (IF).

Este módulo implementa un motor de descarga multi-hilo (Multi-threading) para
obtener los archivos ZIP diarios de la Superintendencia de Pensiones. 

Optimizaciones avanzadas:
    - Concurrencia controlada: Uso de ThreadPoolExecutor para descargas paralelas.
    - Eficiencia de Red: Reutilización de conexiones TCP vía requests.Session.
    - Filtrado Cronológico: Omisión de fines de semana previo a la orquestación.
    - Resiliencia: Gestión de errores aislada por hilo de ejecución.

Estructura de salida:
    data/Precios_IF/{anio}/{mes}/zip/ -> Respaldos binarios.
    data/Precios_IF/{anio}/{mes}/txt/ -> Datos extraídos.
"""

from __future__ import annotations

import io
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import List

from .config import BASE_URL, DEFAULT_PRECIOS_IF_DIR
from .session import crear_sesion
from .logger import configurar_logger

# Configuración de logging profesional
logger = configurar_logger(__name__)

# Mapeo de meses requerido por la estructura de URLs de la Superintendencia
MESES_MAP = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr",
    5: "may", 6: "jun", 7: "jul", 8: "ago",
    9: "sep", 10: "oct", 11: "nov", 12: "dic",
}


def descargar_precios_if_anio(anio: int, max_workers: int = 5) -> None:
    """Orquesta la descarga concurrente de Precios IF para un año completo.

    Esta función actúa como el orquestador principal (Master). Divide el año
    en días hábiles y distribuye la carga de trabajo entre un pool de hilos.

    Args:
        anio: Año calendario a descargar (ej. 2024).
        max_workers: Número de hilos simultáneos. Se recomienda un máximo de 5-8
            para mantener una política de 'politeness' con el servidor oficial.

    Flow:
        1. Identifica todos los días Lunes-Viernes del año.
        2. Inicializa un ThreadPoolExecutor.
        3. Mapea la función worker a cada fecha válida.
        4. Monitorea y reporta el progreso de las tareas completadas.
    """
    contexto = f"PRECIOS_IF {anio}"
    logger.info("[%s] Iniciando orquestación concurrente (%s hilos)", contexto, max_workers)

    # Creamos una sesión compartida. El objeto Session es Thread-Safe para GET.
    # Reutiliza la conexión TCP (Keep-Alive) entre todos los hilos.
    session = crear_sesion()
    
    # 1. Generación de fechas objetivo (Filtrado preventivo de fines de semana)
    fechas_a_procesar: List[date] = []
    current = date(anio, 1, 1)
    end = date(anio, 12, 31)

    while current <= end:
        if current.weekday() < 5:  # Lunes=0, ..., Viernes=4
            fechas_a_procesar.append(current)
        current += timedelta(days=1)

    # 2. Ejecución Concurrente
    total_dias = len(fechas_a_procesar)
    exitos = 0
    errores = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Mapeamos cada fecha a la función worker
        futures = {
            executor.submit(_descargar_dia_worker, session, d): d 
            for d in fechas_a_procesar
        }

        for future in as_completed(futures):
            fecha_job = futures[future]
            try:
                resultado = future.result()
                if resultado:
                    exitos += 1
                else:
                    errores += 1
            except Exception as e:
                logger.error("[%s] Error crítico en hilo para %s: %s", contexto, fecha_job, e)
                errores += 1

    logger.info(
        "[%s] Finalizado. Exitosos: %s | Fallidos/404: %s | Total: %s",
        contexto, exitos, errores, total_dias
    )


def _descargar_dia_worker(session, fecha: date) -> bool:
    """Función de trabajo (Worker) ejecutada de forma asíncrona por cada hilo.

    Responsable de la lógica de red, validación de respuesta y delegación
    de la persistencia a disco.

    Args:
        session: Instancia compartida de requests.Session.
        fecha: Fecha específica a procesar.

    Returns:
        bool: True si el archivo fue procesado, False si no existía (404) o falló.
    """
    mes_str = MESES_MAP[fecha.month]
    zip_name = f"p{fecha:%Y%m%d}.zip"
    url = f"{BASE_URL}/apps/GetFile.php?id=006&namefile={fecha.year}/{mes_str}/{zip_name}"

    try:
        # El timeout es vital para no dejar hilos zombies en caso de red lenta
        response = session.get(url, timeout=25)

        if response.status_code == 200:
            logger.info("  [OK] Descargado: %s", zip_name)
            _persistir_y_extraer(fecha, zip_name, response.content)
            return True
        
        elif response.status_code == 404:
            # Los feriados nacionales devuelven 404, se trata como ausencia esperada
            logger.debug("  [SKIP] No disponible (Feriado/404): %s", zip_name)
            return False
        
        else:
            logger.warning("  [WARN] Status %s para %s", response.status_code, zip_name)
            return False

    except Exception as e:
        logger.error("  [ERROR] Fallo en descarga %s: %s", zip_name, e)
        return False


def _persistir_y_extraer(fecha: date, nombre_zip: str, contenido: bytes) -> None:
    """Gestiona la escritura en disco y la descompresión del dataset.

    Se asegura de mantener la estructura jerárquica: data/Dataset/Año/Mes/Formato/

    Args:
        fecha: Fecha del registro.
        nombre_zip: Nombre del archivo ZIP original.
        contenido: Payload binario recibido.
    """
    # Construcción de rutas basada en la jerarquía del proyecto
    base_path = Path(DEFAULT_PRECIOS_IF_DIR) / str(fecha.year) / f"{fecha.month:02d}"
    zip_dir = base_path / "zip"
    txt_dir = base_path / "txt"

    # Creación atómica de directorios
    zip_dir.mkdir(parents=True, exist_ok=True)
    txt_dir.mkdir(parents=True, exist_ok=True)

    # 1. Guardar ZIP original (Respaldo técnico)
    zip_path = zip_dir / nombre_zip
    zip_path.write_bytes(contenido)

    # 2. Extracción defensiva del contenido
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            for member in z.namelist():
                # Validación de seguridad: Prevenir ataques de ZipSlip
                if member.startswith("/") or ".." in member:
                    continue
                
                target_path = txt_dir / member
                target_path.parent.mkdir(parents=True, exist_ok=True)

                with z.open(member) as src, open(target_path, "wb") as dst:
                    dst.write(src.read())
    except zipfile.BadZipFile:
        logger.error("Archivo corrupto: %s", nombre_zip)