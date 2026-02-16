import pandas as pd

def sp_multiheader_to_long(df: pd.DataFrame, periodo: str) -> pd.DataFrame:

    # 1. Primera columna SIEMPRE TipoInstrumento
    tipo_series = df.iloc[:,0]
    df = df.iloc[:,1:]

    # 2. limpiar métricas
    new_cols = []

    for c1, c2 in df.columns:
        metrica = str(c2)\
            .replace("MMUS$", "MMUSD")\
            .replace("%Fondo", "PCT")
        new_cols.append((c1, metrica))

    df.columns = pd.MultiIndex.from_tuples(new_cols)

    # 3. LONG
    df_long = (
        df
        .stack(level=0)
        .stack(level=0)
        .reset_index()
    )

    df_long.columns = [
        "row_id",
        "AGENTE",
        "METRICA",
        "valor"
    ]

    # 4. reinsertar TipoInstrumento
    df_long["TipoInstrumento"] = tipo_series.values[df_long["row_id"]]
    df_long = df_long.drop(columns="row_id")

    # 5. 👇 AQUI SE AGREGA EL PERIODO
    df_long["PERIODO"] = periodo

    return df_long[
        ["PERIODO","AGENTE","METRICA","TipoInstrumento","valor"]
    ]