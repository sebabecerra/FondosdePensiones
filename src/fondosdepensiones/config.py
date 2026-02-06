"""
Configuración global del proyecto SPensiones.

Este archivo contiene únicamente constantes y valores por defecto.
No debe contener lógica.
"""

from pathlib import Path


BASE_URL = "https://www.spensiones.cl"


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"

DEFAULT_CARTERAS_INVERSIONES_AGREGADA_DIR = DATA_DIR / "Carteras_Inversiones_agregadas"
DEFAULT_EEFF_DIR = DATA_DIR / "Estados_Financieros"
DEFAULT_CARTERAS_INVERSIONES_DIR = DATA_DIR / "Carteras_Inversiones"





