"""
TEST: Convertir SOLO 1 CSV a formato LONG

INPUT:
data/Carteras_Inversiones_agregadas/2025/csv/202501/cuadro_no_1_*.csv

OUTPUT:
cuadro_no_1_long.csv
"""

import pandas as pd
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

CSV_PATH = Path(
    "data/Carteras_Inversiones_agregadas/2025/csv/202501/"
    "cuadro_no_1_cartera_agregada_de_los_fondos_de_pensiones_por_tipo_de_fondo.csv"
)

PERIODO = "202501"


# ============================================================
# CORE
# ============================================================

def wide_to_long(df: pd.DataFrame, periodo: str) -> pd.DataFrame:

    # 1. Primera columna = variables
    df = df.rename(columns={df.columns[0]: "variable"})

    # 2. melt
    df_long = df.melt(
        id_vars=["variable"],
        var_name="fondo_medida",
        value_name="valor"
    )

    # -----------------------------------------
    # split fondo / medida (schema-agnostic)
    # -----------------------------------------
    def split_fondo_medida(s):

        if s.endswith("_mmusd"):
            return s.replace("_mmusd", ""), "mmusd"

        if s.endswith("_pct"):
            return s.replace("_pct", ""), "pct"

        # fondo_total etc.
        return s, None

    tmp = df_long["fondo_medida"].apply(split_fondo_medida)

    df_long["fondo"]  = tmp.apply(lambda x: x[0])
    df_long["medida"] = tmp.apply(lambda x: x[1])

    # 4. agregar periodo
    df_long["periodo"] = periodo

    return df_long[
        ["periodo", "variable", "fondo", "medida", "valor"]
    ]


# ============================================================
# RUN
# ============================================================

df = pd.read_csv(CSV_PATH)

df_long = wide_to_long(df, PERIODO)

OUT = CSV_PATH.with_name("cuadro_no_1_long.csv")

df_long.to_csv(OUT, index=False)

print("✅ LONG generado en:")
print(OUT)