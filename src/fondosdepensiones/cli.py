from __future__ import annotations

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

────────────────────────────────────────────────────────────────────
PERFORMANCE
────────────────────────────────────────────────────────────────────
- Se introduce el parámetro --workers para motores que soportan 
  concurrencia (actualmente: precios_if).
"""



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

# Utilidades de Dominio
from fondosdepensiones.utils_periodos import (
    meses_de_anio, meses_de_rango,
    trimestres_de_anio, trimestres_de_rango
)

def imprimir_separador(titulo: str, workers: int) -> None:
    """Banner visual para logs."""
    print(f"\n{'='*80}")
    print(f"▶ {titulo}")
    print(f"▶ CONFIGURACIÓN: {workers} hilos concurrentes (si aplica)")
    print(f"{'='*80}")

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fondosdescargas",
        description="Plataforma Industrial de Descarga SPensiones Chile",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "tipo",
        choices=[
            "carteras_inversion_agregadas", "carteras_inversion", 
            "eeff", "valores_cuota", "precios_if", "balance_d1", "ambos"
        ],
        help="Dataset a descargar."
    )

    grupo_t = parser.add_mutually_exclusive_group(required=True)
    grupo_t.add_argument("--periodo", help="YYYY o YYYYMM.")
    grupo_t.add_argument("--rango", nargs=2, type=int, metavar=("DESDE", "HASTA"))

    parser.add_argument("--fondo", default="C", choices=["A", "B", "C", "D", "E"])
    parser.add_argument("--workers", type=int, default=5, help="Hilos concurrentes.")

    args = parser.parse_args()

    # --- RESOLUCIÓN DE PERIODOS ---
    periodos: List[str] = []
    es_anual = args.tipo in ("valores_cuota", "precios_if")

    if args.rango:
        d, h = args.rango
        if es_anual: periodos = [str(a) for a in range(d, h + 1)]
        elif args.tipo == "eeff": periodos = trimestres_de_rango(d, h)
        else: periodos = meses_de_rango(d, h)
    else:
        p = args.periodo
        if es_anual:
            if len(p) != 4: parser.error(f"{args.tipo} requiere año (YYYY).")
            periodos = [p]
        elif args.tipo == "eeff":
            periodos = [p] if len(p) == 6 else trimestres_de_anio(int(p))
        else:
            periodos = [p] if len(p) == 6 else meses_de_anio(int(p))

    # --- DESPACHO EXPLÍCITO (Para evitar 'unexpected argument') ---
    for p in periodos:
        imprimir_separador(f"{args.tipo.upper()} | PERIODO: {p}", args.workers)
        
        try:
            if args.tipo == "valores_cuota":
                # Valores cuota NO usa workers, solo fondo
                descargar_valores_cuota(desde_anio=int(p), hasta_anio=int(p), tipo_fondo=args.fondo)
            
            elif args.tipo == "precios_if":
                # Precios IF usa workers pero NO fondo
                descargar_precios_if_anio(anio=int(p), max_workers=args.workers)
            
            elif args.tipo == "balance_d1":
                # Balance D1 es descarga simple de un ZIP
                descargar_balance_d1(periodo=p)
            
            elif args.tipo == "eeff":
                descargar_eeff(periodo=p, max_workers=args.workers)
            
            elif args.tipo == "carteras_inversion_agregadas" or args.tipo == "ambos":
                descargar_carteras(periodo=p, max_workers=args.workers)
            
            if args.tipo == "carteras_inversion" or args.tipo == "ambos":
                descargar_carteras_inversion(periodo=p, max_workers=args.workers)

        except Exception as e:
            print(f"ERROR CRÍTICO en periodo {p}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()