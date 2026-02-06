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
from typing import List

# ------------------------------------------------------------
# Importación de módulos de descarga (NEGOCIO)
# ------------------------------------------------------------
# Nota: estos módulos deben encargarse de:
# - construir URLs
# - descargar
# - parsear/extraer
# - guardar en data/
# El CLI NO hace scraping ni parseo; solo orquesta.

from fondosdepensiones.carteras_inversion_agregadas import descargar_carteras
from fondosdepensiones.carteras_inversion import descargar_carteras_inversion
from fondosdepensiones.eeff import descargar_eeff
from fondosdepensiones.valores_cuota import descargar_valores_cuota
from fondosdepensiones.precios_if import descargar_precios_if_anio
from fondosdepensiones.balance_d1 import descargar_balance_d1


# ============================================================
# UTILIDADES TEMPORALES (SOLO CLI)
# ============================================================
# Estas funciones existen para convertir la “intención del usuario”
# en una lista concreta de períodos “operables” por cada módulo.
#
# Importante:
# - Carteras trabajan a nivel YYYYMM (mensual).
# - EEFF trabaja a nivel YYYYMM (pero sólo trimestres válidos).
# - Valores Cuota y Precios IF trabajan a nivel ANUAL (YYYY).


def meses_de_anio(anio: int) -> List[str]:
    """
    Genera todos los períodos mensuales YYYYMM de un año.

    Ejemplo:
        meses_de_anio(2024)
        -> ["202401", "202402", ..., "202412"]
    """
    return [f"{anio}{m:02d}" for m in range(1, 13)]


def meses_de_rango(desde: int, hasta: int) -> List[str]:
    """
    Genera todos los períodos mensuales YYYYMM entre dos años completos (inclusive).

    Ejemplo:
        meses_de_rango(2024, 2025)
        -> 24 períodos: 202401..202412 y 202501..202512
    """
    periodos: List[str] = []
    for anio in range(desde, hasta + 1):
        periodos.extend(meses_de_anio(anio))
    return periodos


def trimestres_de_anio(anio: int) -> List[str]:
    """
    Genera los períodos trimestrales válidos para EEFF.

    EEFF sólo existe para:
        marzo (03), junio (06), septiembre (09), diciembre (12)

    Ejemplo:
        trimestres_de_anio(2024)
        -> ["202403","202406","202409","202412"]
    """
    return [f"{anio}{m:02d}" for m in (3, 6, 9, 12)]


def trimestres_de_rango(desde: int, hasta: int) -> List[str]:
    """
    Genera todos los períodos trimestrales entre dos años (inclusive).

    Ejemplo:
        trimestres_de_rango(2024, 2025)
        -> ["202403","202406","202409","202412","202503","202506","202509","202512"]
    """
    periodos: List[str] = []
    for anio in range(desde, hasta + 1):
        periodos.extend(trimestres_de_anio(anio))
    return periodos


def _validar_yyyy(valor: str, label: str) -> int:
    """
    Valida y transforma un string YYYY a int.

    Args:
        valor: string que debe representar un año (YYYY)
        label: nombre lógico del argumento para mensajes de error

    Returns:
        int: año

    Raises:
        argparse.ArgumentTypeError: si no cumple el formato esperado
    """
    if len(valor) != 4 or not valor.isdigit():
        raise argparse.ArgumentTypeError(f"{label} debe ser un año en formato YYYY")
    return int(valor)


def _es_trimestre_eeff(periodo_yyyymm: str) -> bool:
    """
    Retorna True si el período YYYYMM corresponde a un trimestre válido EEFF.

    Válidos: MM ∈ {03,06,09,12}
    """
    if len(periodo_yyyymm) != 6 or not periodo_yyyymm.isdigit():
        return False
    mm = int(periodo_yyyymm[4:6])
    return mm in (3, 6, 9, 12)


# ============================================================
# FUNCIÓN PRINCIPAL DEL CLI
# ============================================================

def main() -> None:
    """
    Punto de entrada del CLI.

    Flujo general:
    1) Definir parser y argumentos (con help claro).
    2) Parsear args.
    3) Branch por tipo (cada tipo tiene su semántica temporal).
    4) Expandir períodos / años según corresponda.
    5) Delegar a los módulos.

    Nota:
    - Se imprimen “banners” simples para UX.
    - Los módulos pueden loguear; el CLI solo orquesta.
    """
    parser = argparse.ArgumentParser(
        prog="fondosdescargas",
        description="Descarga de datos oficiales desde SPensiones (Chile)",
    )

    # --------------------------------------------------------
    # Tipo de descarga (obligatorio)
    # --------------------------------------------------------
    # Importante: 'ambos' SOLO tiene sentido para descargas mensuales (carteras).
    # No mezclamos 'ambos' con EEFF/valores/precios porque sus granularidades difieren.
    parser.add_argument(
        "tipo",
        choices=[
            "carteras_inversion_agregadas",
            "carteras_inversion",
            "eeff",
            "valores_cuota",
            "precios_if",
            "balance_d1",
            "ambos",
        ],

        help=(
            "Tipo de información a descargar:\n"
            "  - carteras_inversion_agregadas: Carteras agregadas (mensual)\n"
            "  - carteras_inversion: Carteras de inversión (mensual)\n"
            "  - eeff: Estados financieros (trimestral)\n"
            "  - valores_cuota: Valores cuota AFP (anual)\n"
            "  - precios_if: Precios instrumentos financieros (anual; descarga diaria interna)\n"
            "  - balance_d1: Balance D1 AFP (mensual; ZIP oficial por período)\n"
            "  - ambos: carteras_inversion_agregadas + carteras_inversion (mensual)\n"
        ),
    )

    # --------------------------------------------------------
    # Selección temporal: --periodo o --rango (mutuamente excluyentes)
    # --------------------------------------------------------
    # Regla general:
    # - Carteras/EEFF aceptan YYYYMM o YYYY o --rango
    # - Valores cuota / precios_if aceptan solo YYYY o --rango
    grupo = parser.add_mutually_exclusive_group(required=True)

    grupo.add_argument(
        "--periodo",
        help=(
            "Período único.\n"
            "  - Carteras: YYYYMM (mes) o YYYY (año completo)\n"
            "  - EEFF: YYYYMM (solo 03/06/09/12) o YYYY (año completo)\n"
            "  - valores_cuota / precios_if: YYYY (año completo)\n"
        ),
    )

    grupo.add_argument(
        "--rango",
        nargs=2,
        type=int,
        metavar=("DESDE", "HASTA"),
        help=(
            "Rango de años completos (inclusive).\n"
            "Ejemplo: --rango 2024 2025"
        ),
    )

    # --------------------------------------------------------
    # Parámetros específicos (solo para valores_cuota)
    # --------------------------------------------------------
    parser.add_argument(
        "--fondo",
        default="C",
        choices=["A", "B", "C", "D", "E"],
        help="Tipo de fondo (solo aplica a valores_cuota). Default: C",
    )

    args = parser.parse_args()

    # ========================================================
    # 1) VALORES CUOTA (ANUAL)
    # ========================================================
    # - Acepta: --periodo YYYY  o  --rango YYYY YYYY
    # - Rechaza: --periodo YYYYMM
    if args.tipo == "valores_cuota":
        if args.periodo:
            # Debe ser YYYY
            if len(args.periodo) != 4:
                parser.error("valores_cuota solo admite años completos (YYYY)")
            desde = hasta = int(args.periodo)
        else:
            desde, hasta = args.rango

        print("=" * 60)
        print(f"▶ DESCARGANDO VALORES CUOTA ({desde}-{hasta}) FONDO {args.fondo}")
        print("=" * 60)

        descargar_valores_cuota(
            desde_anio=desde,
            hasta_anio=hasta,
            tipo_fondo=args.fondo,
        )
        return

    # ========================================================
    # 2) PRECIOS IF (ANUAL; interno DIARIO)
    # ========================================================
    # - Acepta: --periodo YYYY  o  --rango YYYY YYYY
    # - Rechaza: --periodo YYYYMM
    #
    # Notas:
    # - El módulo descarga_precios_if_anio(anio) itera por día (pYYYYMMDD.zip).
    # - El CLI NO gestiona fechas diarias; solo años.
    if args.tipo == "precios_if":
        if args.periodo:
            # Debe ser YYYY
            if len(args.periodo) != 4:
                parser.error("precios_if solo admite años completos (YYYY)")
            desde = hasta = int(args.periodo)
        else:
            desde, hasta = args.rango

        for anio in range(desde, hasta + 1):
            print("=" * 60)
            print(f"▶ DESCARGANDO PRECIOS IF (AÑO {anio})")
            print("=" * 60)

            descargar_precios_if_anio(anio)

        return

    # ========================================================
    # 2.5) BALANCE D1 (MENSUAL)
    # ========================================================
    # - Acepta:
    #   * --periodo YYYYMM (un mes)
    #   * --periodo YYYY   (expande a 12 meses)
    #   * --rango YYYY YYYY (expande meses del rango)
    #
    # Notas importantes:
    # - Balance D1 es un archivo mensual oficial (ZIP).
    # - Internamente replica el botón "Buscar" del formulario D1.
    # - El CLI NO conoce formularios ni botones: solo períodos.
    # - La lógica de descarga vive completamente en balance_d1.py
    if args.tipo == "balance_d1":

        # -------------------------
        # Expansión temporal (MISMA que Carteras)
        # -------------------------
        if args.periodo:
            if len(args.periodo) == 6:
                periodos = [args.periodo]

            elif len(args.periodo) == 4:
                periodos = meses_de_anio(int(args.periodo))

            else:
                parser.error(
                    "balance_d1 admite --periodo YYYYMM (mes) o YYYY (año)"
                )
        else:
            periodos = meses_de_rango(*args.rango)

        # -------------------------
        # Ejecución
        # -------------------------
        for p in periodos:
            print("=" * 60)
            print(f"▶ DESCARGANDO BALANCE D1 ({p})")
            print("=" * 60)

            descargar_balance_d1(p)

        return

    # ========================================================
    # 3) EEFF (TRIMESTRAL)
    # ========================================================
    # - Acepta:
    #   * --periodo YYYYMM (pero SOLO si MM es 03/06/09/12)
    #   * --periodo YYYY   (expande a 4 trimestres)
    #   * --rango YYYY YYYY (expande a trimestres de esos años)
    if args.tipo == "eeff":
        if args.periodo:
            if len(args.periodo) == 6:
                # Validar que sea trimestre válido
                if not _es_trimestre_eeff(args.periodo):
                    parser.error("EEFF solo admite YYYYMM con MM en {03,06,09,12}")
                periodos = [args.periodo]

            elif len(args.periodo) == 4:
                periodos = trimestres_de_anio(int(args.periodo))

            else:
                parser.error("EEFF admite --periodo YYYYMM (trimestre) o YYYY (año)")
        else:
            periodos = trimestres_de_rango(*args.rango)

        for p in periodos:
            print("=" * 60)
            print(f"▶ DESCARGANDO EEFF ({p})")
            print("=" * 60)
            descargar_eeff(p)

        return

    # ========================================================
    # 4) CARTERAS (MENSUAL) + AMBOS (CARTERAS)
    # ========================================================
    # - Acepta:
    #   * --periodo YYYYMM (un mes)
    #   * --periodo YYYY   (expande a 12 meses)
    #   * --rango YYYY YYYY (expande meses del rango)
    #
    # Nota:
    # - 'ambos' = carteras_inversion_agregadas + carteras_inversion.
    # - No incluimos EEFF aquí porque es trimestral.
    if args.periodo:
        if len(args.periodo) == 6:
            periodos = [args.periodo]
        elif len(args.periodo) == 4:
            periodos = meses_de_anio(int(args.periodo))
        else:
            parser.error("Carteras admite --periodo YYYYMM (mes) o YYYY (año)")
    else:
        periodos = meses_de_rango(*args.rango)

    for p in periodos:
        print("=" * 60)
        print(f"▶ PROCESANDO CARTERAS ({p})")
        print("=" * 60)

        if args.tipo in ("carteras_inversion_agregadas", "ambos"):
            descargar_carteras(p)

        if args.tipo in ("carteras_inversion", "ambos"):
            descargar_carteras_inversion(p)


# ============================================================
# ENTRYPOINT
# ============================================================
if __name__ == "__main__":
    main()