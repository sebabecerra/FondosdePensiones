# ============================================
# BUILD LONG (append-ready)
# ============================================

import pandas as pd
from pathlib import Path
from fondosdepensiones.long import sp_multiheader_to_long


# 👇 archivo que estás probando ahora
file = Path(
"data/Carteras_Inversiones_agregadas/2020/csv/202010/cuadro_no_1_cartera_agregada_de_los_fondos_de_pensiones_por_tipo_de_fondo.csv"
)

# ---------------------------------
# 1. Detectar PERIODO desde carpeta
# ---------------------------------
periodo = file.parent.name

print(f"Periodo detectado: {periodo}")


# ---------------------------------
# 2. Leer CSV SP (doble header)
# ---------------------------------
df = pd.read_csv(file, header=[0,1])


# ---------------------------------
# 3. LONG (ya trae PERIODO adentro)
# ---------------------------------
df_long = sp_multiheader_to_long(
    df=df,
    periodo=periodo
)

print(df_long.head())


# ---------------------------------
# 4. Guardar test
# ---------------------------------
df_long.to_csv("test_long.csv", index=False)

print("✅ LONG guardado en test_long.csv")