"""
Auditoría de datos descargados – fondosdepensiones

Este script inspecciona el directorio data/ y responde:

- Qué información existe
- Cuántos archivos hay por tipo
- Qué períodos están cubiertos
- Qué períodos faltan (según reglas del proyecto)

NO descarga nada.
NO modifica archivos.
"""

from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")


# ============================================================
# UTILIDADES
# ============================================================

def meses_entre(desde: int, hasta: int):
    """Genera YYYYMM entre dos años (inclusive)."""
    periodos = []
    for anio in range(desde, hasta + 1):
        for mes in range(1, 13):
            periodos.append(f"{anio}{mes:02d}")
    return periodos


def trimestres_entre(desde: int, hasta: int):
    """Genera YYYYMM trimestrales (03,06,09,12)."""
    periodos = []
    for anio in range(desde, hasta + 1):
        for mes in (3, 6, 9, 12):
            periodos.append(f"{anio}{mes:02d}")
    return periodos


# ============================================================
# AUDITORÍAS POR TIPO
# ============================================================

def auditar_carpeta_mensual(nombre: str, ruta: Path, desde: int, hasta: int):
    print(f"\n📂 {nombre}")
    csv_dir = ruta / "csv"

    existentes = sorted(p.name for p in csv_dir.glob("*") if p.is_dir())
    esperados = meses_entre(desde, hasta)

    faltantes = sorted(set(esperados) - set(existentes))

    print(f"  ✔ Períodos existentes : {len(existentes)}")
    print(f"  ❌ Períodos faltantes  : {len(faltantes)}")

    if faltantes:
        print(f"  → Faltan: {faltantes[:6]}{' ...' if len(faltantes) > 6 else ''}")


def auditar_eeff(ruta: Path, desde: int, hasta: int):
    print("\n📂 EEFF (trimestral)")
    csv_dir = ruta / "csv"

    existentes = sorted(p.name for p in csv_dir.glob("*") if p.is_dir())
    esperados = trimestres_entre(desde, hasta)

    faltantes = sorted(set(esperados) - set(existentes))

    print(f"  ✔ Trimestres existentes : {len(existentes)}")
    print(f"  ❌ Trimestres faltantes  : {len(faltantes)}")

    if faltantes:
        print(f"  → Faltan: {faltantes}")


def auditar_anual(nombre: str, ruta: Path, desde: int, hasta: int):
    print(f"\n📂 {nombre} (anual)")
    existentes = sorted(p.name for p in ruta.glob("*") if p.is_dir())
    esperados = [str(a) for a in range(desde, hasta + 1)]

    faltantes = sorted(set(esperados) - set(existentes))

    print(f"  ✔ Años existentes : {len(existentes)}")
    print(f"  ❌ Años faltantes  : {faltantes if faltantes else '—'}")


# ============================================================
# MAIN
# ============================================================

def main():
    hoy = datetime.today()
    anio_actual = hoy.year

    DESDE = 2018
    HASTA = anio_actual

    print("🧾 AUDITORÍA DE DATOS – fondosdepensiones")
    print("=" * 60)
    print(f"Rango esperado: {DESDE}–{HASTA}")

    auditar_carpeta_mensual(
        "Carteras Inversión Agregadas",
        DATA_DIR / "Carteras_Inversiones_agregadas",
        DESDE,
        HASTA,
    )

    auditar_carpeta_mensual(
        "Carteras Inversión",
        DATA_DIR / "Carteras_Inversiones",
        DESDE,
        HASTA,
    )

    auditar_eeff(
        DATA_DIR / "Estados_Financieros",
        DESDE,
        HASTA,
    )

    auditar_anual(
        "Valores Cuota",
        DATA_DIR / "valores_cuota",
        DESDE,
        HASTA,
    )

    auditar_anual(
        "Precios IF",
        DATA_DIR / "precios_if",
        DESDE,
        HASTA,
    )

    auditar_anual(
        "Balance D1",
        DATA_DIR / "balance_d1",
        DESDE,
        HASTA,
    )


if __name__ == "__main__":
    main()