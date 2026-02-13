"""
Configuración global del proyecto SPensiones.

Este archivo centraliza las rutas del proyecto. Utiliza resolución de rutas
absolutas para asegurar que los scripts funcionen independientemente de desde
dónde sean invocados.
"""

from pathlib import Path

# --- URL BASE ---
BASE_URL = "https://www.spensiones.cl"

# --- RESOLUCIÓN DE RUTAS ---
# Ubicación de este archivo: src/fondosdepensiones/config.py
# resolve() convierte rutas relativas en absolutas del sistema.
_CURRENT_FILE = Path(__file__).resolve()

# PROJECT_ROOT: Subimos 2 niveles desde config.py para llegar a la raíz del proyecto.
# Nivel 0: config.py
# Nivel 1: fondosdepensiones/
# Nivel 2: src/
# Nivel 3: Raíz del proyecto (donde debería estar /data)
PROJECT_ROOT = _CURRENT_FILE.parents[2]

# DATA_DIR: Es la carpeta donde se almacenan todos los resultados.
# Se recomienda que esté en la raíz para fácil acceso.
DATA_DIR = PROJECT_ROOT / "data"

# --- DIRECTORIOS DE DATASETS ---
# Definimos las rutas hijas basadas en DATA_DIR
DEFAULT_CARTERAS_INVERSIONES_AGREGADA_DIR = DATA_DIR / "Carteras_Inversiones_agregadas"
DEFAULT_EEFF_DIR = DATA_DIR / "Estados_Financieros"
DEFAULT_CARTERAS_INVERSIONES_DIR = DATA_DIR / "Carteras_Inversiones"
DEFAULT_VALORES_CUOTA_DIR = DATA_DIR / "Valores_Cuota"
DEFAULT_PRECIOS_IF_DIR = DATA_DIR / "Precios_IF"
DEFAULT_BALANCE_D1_DIR = DATA_DIR / "Balance_D1"

# --- VALIDACIÓN INICIAL ---
# En Google, las configuraciones intentan asegurar que el entorno sea válido.
# Esto crea la carpeta data si no existe apenas se importa el módulo.
DATA_DIR.mkdir(parents=True, exist_ok=True)