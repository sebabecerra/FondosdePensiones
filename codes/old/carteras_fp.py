# carteras_fp.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from urllib.parse import urljoin
from typing import List, Optional

BASE_URL = "https://www.spensiones.cl"

HTML_DIR = "data/cartera_agregada/html/mensual"
CSV_MENSUAL_DIR = "data/cartera_agregada/csv/mensual"
CSV_AGREGADO_DIR = "data/cartera_agregada/csv/agregado"

os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(CSV_MENSUAL_DIR, exist_ok=True)
os.makedirs(CSV_AGREGADO_DIR, exist_ok=True)

FONDOS = ["A", "B", "C", "D", "E", "TOTAL"]

METRICAS = ["MMUSD", "PCT"]


# -------------------------
# Helpers internos
# -------------------------
def _crear_sesion() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{BASE_URL}/apps/centroEstadisticas/paginaCuadrosCCEE.php"
    })
    return s


def _generar_periodos(desde: int, hasta: int) -> List[str]:
    return [
        f"{y}{str(m).zfill(2)}"
        for y in range(desde, hasta + 1)
        for m in range(1, 13)
    ]


def _procesar_periodo(periodo: str, session: requests.Session) -> Optional[str]:

    url = (
        f"{BASE_URL}/apps/loadCarteras/loadCarAgr.php"
        f"?menu=sci&menuN1=estfinfp&menuN2=NOID"
        f"&orden=20&periodo={periodo}&ext=.php"
    )

    resp = session.get(url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    link = None
    for a in soup.find_all("a", href=True):
        if "genera_xsl2xls.php" in a["href"]:
            link = urljoin(BASE_URL, a["href"])
            break

    if not link:
        return None

    html_resp = session.get(link, timeout=60)
    html_resp.raise_for_status()

    html_text = (
        html_resp.content
        .decode("utf-8")
        .replace(".", "")
        .replace(",", ".")
    )

    html_path = f"{HTML_DIR}/cartera_{periodo}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_text)

    df = pd.read_html(html_path)[0]
    df = df.dropna(how="all").reset_index(drop=True)

    cols = []
    for i in range(len(df.columns)):
        if i == 0:
            cols.append("TipoInstrumento")
        else:
            idx = i - 1
            fondo = FONDOS[(idx // 2) % len(FONDOS)]
            metrica = METRICAS[idx % 2]
            cols.append(f"Fondo_{fondo}_{metrica}")

    df.columns = cols
    df["PERIODO"] = periodo

    df_long = (
        df.melt(
            id_vars=["PERIODO", "TipoInstrumento"],
            var_name="variable",
            value_name="valor"
        )
        .dropna(subset=["valor"])
        .reset_index(drop=True)
    )

    tmp = (
        df_long["variable"]
        .str.replace("Fondo_", "", regex=False)
        .str.split("_", expand=True)
    )

    df_long["fondo"] = tmp[0]
    df_long["metrica"] = tmp[1]

    df_long = df_long[
        ["PERIODO", "TipoInstrumento", "fondo", "metrica", "valor"]
    ]

    out_csv = f"{CSV_MENSUAL_DIR}/cartera_{periodo}.csv"
    df_long.to_csv(out_csv, index=False)

    return out_csv


# -------------------------
# FUNCIÓN PÚBLICA
# -------------------------
def descargar_carteras_agregadas_FP(
    desde: int,
    hasta: int,
    append: bool = False,
    output: str = "cartera_total.csv"
) -> None:

    session = _crear_sesion()
    periodos = _generar_periodos(desde, hasta)

    dfs = []

    for p in periodos:
        print(f"▶ Procesando {p}")
        try:
            csv = _procesar_periodo(p, session)
            if csv:
                print("  ✅ OK")
                if append:
                    dfs.append(pd.read_csv(csv))
            else:
                print("  ⚠️ Sin datos")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    if append and dfs:
        df_all = pd.concat(dfs, ignore_index=True)
        out = f"{CSV_AGREGADO_DIR}/{output}"
        df_all.to_csv(out, index=False)
        print(f"\n📦 CSV agregado generado: {out}")