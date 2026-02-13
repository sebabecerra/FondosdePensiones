from __future__ import annotations

"""CLI del proyecto fondosdepensiones.

Este módulo orquesta las descargas pasando a cada motor exactamente los 
parámetros que su firma de función soporta, evitando errores de 'unexpected argument'.
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