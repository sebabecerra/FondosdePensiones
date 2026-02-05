# src/fondosdepensiones/cli.py
"""
CLI del proyecto fondosdepensiones.

Permite ejecutar descargas desde línea de comandos en dos modos:
- Período único (YYYYMM)
- Rango de años (YYYY–YYYY)
"""

from __future__ import annotations

import argparse

from fondosdepensiones.carteras import (
    descargar_carteras,
    descargar_carteras_rango,
)
from fondosdepensiones.fecu import (
    descargar_fecu,
    descargar_fecu_rango,
)

from fondosdepensiones.carteras_inversion import (
    descargar_carteras_inversion,
    descargar_carteras_inversion_rango
) 


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga datos desde SPensiones (Carteras y FECU)"
    )

    parser.add_argument(
    "tipo",
    choices=[
        "carteras",
        "carteras_inversion",
        "fecu",
        "ambos"
    ],
    help="Tipo de descarga"
)


    grupo = parser.add_mutually_exclusive_group(required=True)

    grupo.add_argument(
        "--periodo",
        help="Período único en formato YYYYMM (ej: 202401)",
    )

    grupo.add_argument(
        "--rango",
        nargs=2,
        type=int,
        metavar=("DESDE", "HASTA"),
        help="Rango de años (ej: 2024 2025)",
    )

    args = parser.parse_args()

    # --------------------------------------------------
    # MODO PERÍODO ÚNICO
    # --------------------------------------------------
    if args.periodo:
        periodo = args.periodo

        if args.tipo in ("carteras", "ambos"):
            descargar_carteras(periodo)

        if args.tipo in ("fecu", "ambos"):
            descargar_fecu(periodo)

        if args.tipo in ("carteras_inversion", "ambos"):
            descargar_carteras_inversion(periodo)


    # --------------------------------------------------
    # MODO RANGO DE AÑOS
    # --------------------------------------------------
    if args.rango:
        desde, hasta = args.rango

        if args.tipo in ("carteras", "ambos"):
            descargar_carteras_rango(desde, hasta)

        if args.tipo in ("fecu", "ambos"):
            descargar_fecu_rango(desde, hasta)

        if args.tipo in ("carteras_inversion", "ambos"):
            descargar_carteras_inversion_rango(periodo)



if __name__ == "__main__":
    main()
