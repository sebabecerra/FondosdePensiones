"""Módulo de utilidades de Entrada/Salida y Transformación de Datos.

Este módulo centraliza la persistencia de archivos y la normalización de 
DataFrames extraídos de HTML. Implementa una tubería de limpieza que 
elimina artefactos visuales y corrige tipos de datos financieros.
"""

from __future__ import annotations

import os
import re
from io import StringIO
from typing import Optional

import pandas as pd
import numpy as np

from .logger import configurar_logger

logger = configurar_logger(__name__)


def limpiar_df(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica una tubería de limpieza industrial al DataFrame.

    Acciones:
        1. Elimina filas y columnas completamente vacías.
        2. Aplana MultiIndex si existen encabezados combinados.
        3. Elimina filas de 'Totales', 'Notas' y pie de página.
        4. Normaliza strings (quitar espacios extra).
        5. Convierte columnas numéricas (formato CL: 1.234,56 -> 1234.56).

    Args:
        df: DataFrame crudo extraído por pandas.read_html.

    Returns:
        DataFrame normalizado.
    """
    if df.empty:
        return df

    # 1. Copia defensiva
    working_df = df.copy()

    # 2. Manejo de MultiIndex (Headers combinados)
    # Si las columnas son una tupla, las unimos con guion bajo
    if isinstance(working_df.columns, pd.MultiIndex):
        working_df.columns = [
            "_".join([str(level) for level in col if "Unnamed" not in str(level)]).strip("_")
            for col in working_df.columns.values
        ]

    # 3. Limpieza de ruido estructural
    # Eliminar filas/columnas 100% NaN
    working_df = working_df.dropna(how="all").dropna(axis=1, how="all")

    # 4. Filtro de filas de control (Totales y Metadatos)
    # Buscamos palabras clave que suelen indicar filas que no son registros individuales
    terminos_basura = r"total|subtotal|fuente:|nota:|glosa:|confección"
    
    # Creamos una máscara booleana: True si la fila NO parece ser basura
    # Solo revisamos las primeras columnas que suelen tener las etiquetas
    if not working_df.empty:
        mask = working_df.iloc[:, 0].astype(str).str.contains(terminos_basura, case=False, na=False)
        working_df = working_df[~mask]

    # 5. Normalización de contenido y conversión numérica
    for col in working_df.columns:
        # Limpiar espacios en blanco en strings
        if working_df[col].dtype == "object":
            working_df[col] = working_df[col].astype(str).str.strip()

            # Identificar columnas que parecen números en formato chileno (1.234,56)
            # Regla: Contiene coma y solo dígitos/puntos/signo menos
            if working_df[col].str.contains(r"^-?\d+(\.\d+)*,\d+$", na=False).any():
                working_df[col] = (
                    working_df[col]
                    .str.replace(".", "", regex=False)  # Quitar miles
                    .str.replace(",", ".", regex=False)  # Cambiar decimal
                )
                working_df[col] = pd.to_numeric(working_df[col], errors="coerce")

    # 6. Re-indexar tras la limpieza de filas
    working_df = working_df.reset_index(drop=True)

    return working_df


def guardar_html_y_csv(
    html: str,
    nombre: str,
    html_dir: str,
    csv_dir: str
) -> None:
    """Guarda el HTML original y exporta una versión limpia en CSV.

    Args:
        html: Contenido HTML crudo.
        nombre: Nombre base del archivo (sin extensión).
        html_dir: Directorio para el backup HTML.
        csv_dir: Directorio para el dato procesado (CSV).
    """
    os.makedirs(html_dir, exist_ok=True)
    os.makedirs(csv_dir, exist_ok=True)

    # 1. Persistencia de la 'Fuente de Verdad' (HTML Crudo)
    html_path = os.path.join(html_dir, f"{nombre}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # 2. Extracción y Limpieza
    try:
        # Usamos StringIO para evitar warnings de futuros de Pandas
        tablas = pd.read_html(StringIO(html))
        
        if not tablas:
            logger.warning("No se encontraron tablas en %s", nombre)
            return

        # Procesamos la tabla principal (usualmente la primera)
        df_limpio = limpiar_df(tablas[0])

        if df_limpio.empty:
            logger.warning("La tabla en %s quedó vacía tras la limpieza", nombre)
            return

        # 3. Exportación
        csv_path = os.path.join(csv_dir, f"{nombre}.csv")
        df_limpio.to_csv(csv_path, index=False, encoding="utf-8-sig")
        
        logger.debug("CSV guardado exitosamente: %s", csv_path)

    except Exception as e:
        logger.error("Falla crítica procesando tabla %s: %s", nombre, e)