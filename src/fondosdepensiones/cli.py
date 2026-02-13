# src/fondosdepensiones/cli.py
"""
CLI del proyecto fondosdepensiones.

Este módulo define la interfaz de línea de comandos (CLI) del proyecto.
Su única responsabilidad es:

1) Interpretar la intención temporal del usuario (mes, año, rango).
2) Validar combinaciones permitidas (según semántica del dato).
3) Delegar la ejecución a los módulos de descarga (sin duplicar lógica de negocio).

────────────────────────────────────────────────────────────────────
SEMÁNTICA TEMPORAL (la regla de oro)
────────────────────────────────────────────────────────────────────
Cada “tipo” de dato tiene su propia granularidad:

- Carteras (agregadas / inversión):
    * Mensual:      YYYYMM
    * Año completo: YYYY    → expande a 12 meses (YYYY01..YYYY12)
    * Rango:        YYYY YYYY → expande a todos los meses entre ambos años

- EEFF:
    * Trimestral:   solo existen para meses 03, 06, 09, 12
    * Mensual:      se acepta YYYYMM SOLO si es uno de esos trimestres
    * Año completo: YYYY    → expande a 4 trimestres (YYYY03, YYYY06, YYYY09, YYYY12)
    * Rango:        YYYY YYYY → expande a trimestres correspondientes

- Valores Cuota:
    * Anual:        YYYY
    * Rango:        YYYY YYYY
    * NO admite:    YYYYMM (porque la descarga se construye por año)
      Nota: internamente la serie es diaria, pero el “control” en CLI es anual.

- Precios IF (Instrumentos Financieros):
    * Anual:        YYYY
    * Rango:        YYYY YYYY
    * NO admite:    YYYYMM
      Nota: internamente itera DIARIO (pYYYYMMDD.zip), pero el input del CLI es anual.

- Balance D1:
    * Mensual:      YYYYMM
    * Año completo: YYYY    → expande a 12 meses
    * Rango:        YYYY YYYY → expande a meses completos
    * Nota:
        - Replica el botón “Buscar” del formulario D1
        - Descarga ZIP oficial mensual (contiene CSV)

────────────────────────────────────────────────────────────────────
EJEMPLOS DE USO
────────────────────────────────────────────────────────────────────
# Carteras (mensual)
fondosdescargas carteras_inversion_agregadas --periodo 202401

# Carteras (año completo)
fondosdescargas carteras_inversion --periodo 2024

# Carteras (rango de años)
fondosdescargas carteras_inversion_agregadas --rango 2024 2025

# EEFF (trimestre puntual)
fondosdescargas eeff --periodo 202412

# EEFF (año completo → 4 trimestres)
fondosdescargas eeff --periodo 2024

# Valores Cuota (año completo)
fondosdescargas valores_cuota --periodo 2024 --fondo C

# Valores Cuota (rango)
fondosdescargas valores_cuota --rango 2020 2024 --fondo A

# Precios IF (año completo)
fondosdescargas precios_if --periodo 2025

# Precios IF (rango)
fondosdescargas precios_if --rango 2022 2025

# Un mes
fondosdescargas balance_d1 --periodo 202505

# Año completo
fondosdescargas balance_d1 --periodo 2024

# Rango
fondosdescargas balance_d1 --rango 2020 2024
"""


from __future__ import annotations
import argparse
import sys
from typing import List

# Motores de Descarga
from fondosdepensiones.carteras_inversion_agregadas import descargar_carteras
from fondosdepensiones.carteras_inversion import descargar_carteras_inversion
from fondosdepensiones.eeff import descargar_eeff
from fondosdepensiones.valores_cuota import descargar_valores_cuota
from fondosdepensiones.precios_if import descargar_precios_if_anio
from fondosdepensiones.balance_d1 import descargar_balance_d1

from fondosdepensiones.config import DATA_DIR, PROJECT_ROOT

def main() -> None:
    # --- ESTO ES PARA DEBUG ---
    print("\n" + "!"*40)
    print(f"DEBUG: El código está en: {__file__}")
    print(f"DEBUG: La raíz del proyecto es: {PROJECT_ROOT.absolute()}")
    print(f"DEBUG: Los datos se guardarán en: {DATA_DIR.absolute()}")
    print("!"*40 + "\n")

# Lógica de Dominio Temporal
from fondosdepensiones.utils_periodos import (
    meses_de_anio,
    meses_de_rango,
    trimestres_de_anio,
    trimestres_de_rango,
    es_trimestre_eeff
)

def imprimir_separador(titulo: str) -> None:
    """Banner visual para logs de ejecución."""
    print(f"\n{'='*80}\n▶ {titulo}\n{'='*80}")

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fondosdescargas",
        description="Herramienta Industrial de Descarga SPensiones (Chile)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "tipo",
        choices=[
            "carteras_inversion_agregadas", "carteras_inversion",
            "eeff", "valores_cuota", "precios_if", "balance_d1", "ambos",
        ],
        help="Tipo de dataset oficial a descargar."
    )

    grupo_t = parser.add_mutually_exclusive_group(required=True)
    grupo_t.add_argument("--periodo", help="YYYY o YYYYMM.")
    grupo_t.add_argument("--rango", nargs=2, type=int, metavar=("DESDE", "HASTA"))

    parser.add_argument("--fondo", default="C", choices=["A", "B", "C", "D", "E"])

    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # 1. PROCESOS ANUALES (Valores Cuota / Precios IF)
    # -------------------------------------------------------------------------
    if args.tipo in ("valores_cuota", "precios_if"):
        if args.periodo:
            if len(args.periodo) != 4:
                parser.error(f"{args.tipo} requiere año completo (YYYY).")
            desde = hasta = int(args.periodo)
        else:
            desde, hasta = args.rango

        if args.tipo == "valores_cuota":
            imprimir_separador(f"VALORES CUOTA | FONDO {args.fondo} | {desde}-{hasta}")
            descargar_valores_cuota(desde_anio=desde, hasta_anio=hasta, tipo_fondo=args.fondo)
        else:
            for anio in range(desde, hasta + 1):
                imprimir_separador(f"PRECIOS IF | AÑO {anio}")
                descargar_precios_if_anio(anio)
        return

    # -------------------------------------------------------------------------
    # 2. PROCESOS PERIÓDICOS (Carteras / EEFF / Balance D1)
    # -------------------------------------------------------------------------
    periodos: List[str] = []

    if args.tipo == "eeff":
        if args.periodo:
            if len(args.periodo) == 6:
                if not es_trimestre_eeff(args.periodo):
                    parser.error("EEFF: Mes debe ser cierre trimestral (03, 06, 09, 12).")
                periodos = [args.periodo]
            elif len(args.periodo) == 4:
                periodos = trimestres_de_anio(int(args.periodo))
        else:
            periodos = trimestres_de_rango(*args.rango)
    else:
        # Carteras y Balance D1
        if args.periodo:
            if len(args.periodo) == 6:
                periodos = [args.periodo]
            elif len(args.periodo) == 4:
                periodos = meses_de_anio(int(args.periodo))
        else:
            periodos = meses_de_rango(*args.rango)

    # Ejecución iterativa
    for p in periodos:
        imprimir_separador(f"DESCARGANDO {args.tipo.upper()} | PERIODO {p}")
        try:
            if args.tipo == "eeff":
                descargar_eeff(p)
            elif args.tipo == "balance_d1":
                descargar_balance_d1(p)
            else:
                if args.tipo in ("carteras_inversion_agregadas", "ambos"):
                    descargar_carteras(p)
                if args.tipo in ("carteras_inversion", "ambos"):
                    descargar_carteras_inversion(p)
        except Exception as e:
            print(f"ERROR: Falló descarga de {p}. Saltando... ({e})", file=sys.stderr)

if __name__ == "__main__":
    main()