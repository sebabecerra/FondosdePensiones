"""
Configuración central de logging del proyecto.
"""

import logging
import sys


def configurar_logger(nombre: str = "fondosdepensiones"):
    logger = logging.getLogger(nombre)

    if logger.handlers:
        return logger  # evita duplicar handlers

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
