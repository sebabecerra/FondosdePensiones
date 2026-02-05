import os
from typing import Optional, List

import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.spensiones.cl"

HTML_DIR = "data/carteras_fondo/html/mensual"
CSV_DIR  = "data/carteras_fondo/csv/mensual"
CSV_AGREGADO_DIR = "data/carteras_fondo/csv/agregado"

os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(CSV_AGREGADO_DIR, exist_ok=True)

FONDOS = {
    "A": "Fondo A",
    "B": "Fondo B",
    "C": "Fondo C",
    "D": "Fondo D",
    "E": "Fondo E",
    "TOTAL": "Total de Fondos",
}


# =================================================
# Helpers
# =================================================
def _crear_sesion() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{BASE_URL}/apps/centroEstadisticas/paginaCuadrosCCEE.php",
    })
    return s


def _pagina_intermedia(periodo: str, session: requests.Session) -> str:
    url = (
        f"{BASE_URL}/apps/loadCarteras/loadCarAgr.php"
        f"?menu=sci&menuN1=estfinfp&menuN2=NOID"
        f"&orden=20&periodo={periodo}&ext=.php"
    )
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def _extraer_link_html_de_fila(
    soup: BeautifulSoup, etiqueta_fondo: str
) -> Optional[str]:

    target = etiqueta_fondo.strip().casefold()

    for row in soup.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) < 2:
            continue

        texto = tds[1].get_text(strip=True).casefold()
        if texto != target:
            continue

        for a in row.find_all("a", href=True):
            href = a["href"]
            if "genera_xsl" in href:
                return urljoin(BASE_URL, href)

    return None


# =================================================
# CORE
# =================================================
def _descargar_fondo(
    periodo: str,
    fondo_key: str,
    session: requests.Session
) -> Optional[str]:

    etiqueta = FONDOS[fondo_key]

    soup = BeautifulSoup(
        _pagina_intermedia(periodo, session),
        "html.parser"
    )

    link = _extraer_link_html_de_fila(soup, etiqueta)
    if not link:
        return None

    html_resp = session.get(link, timeout=60)
    html_resp.raise_for_status()

    html_text = (
        html_resp.content
        .decode("utf-8", errors="ignore")
        .replace(".", "")
        .replace(",", ".")
    )

    html_path = f"{HTML_DIR}/cartera_{fondo_key}_{periodo}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_text)

    # =============================
    # PARSE
    # =============================
    df = pd.read_html(html_path, header=[0, 1])[0]

    df.columns = [f"{c1}_{c2}".strip() for c1, c2 in df.columns]

    df.columns = (
        df.columns
        .str.replace("MMUS\\$", "MMUSD", regex=True)
        .str.replace("%Fondo", "PCT", regex=False)
    )

    tipo_col = df.columns[0]

    # =============================
    # LONG
    # =============================
    df_long = (
        df
        .melt(
            id_vars=[tipo_col],
            var_name="afp_metrica",
            value_name="valor"
        )
        .dropna(subset=["valor"])
    )

    tmp = df_long["afp_metrica"].str.rsplit("_", n=1, expand=True)
    df_long["AFP"] = tmp[0]
    df_long["METRICA"] = tmp[1]

    df_long = df_long.rename(columns={tipo_col: "TipoInstrumento"})
    df_long["PERIODO"] = periodo
    df_long["FONDO"] = fondo_key

    df_long = df_long[
        ["PERIODO", "FONDO", "AFP", "METRICA", "TipoInstrumento", "valor"]
    ]

    out_csv = f"{CSV_DIR}/cartera_{fondo_key}_{periodo}_long.csv"
    df_long.to_csv(out_csv, index=False)

    return out_csv


# =================================================
# FUNCIÓN PÚBLICA (CON APPEND)
# =================================================
def descargar_carteras_por_fondo(
    desde: int,
    hasta: int,
    append: bool = False,
    output: str = "carteras_fondo_total.csv"
) -> None:

    session = _crear_sesion()
    dfs: List[pd.DataFrame] = []

    for year in range(desde, hasta + 1):
        for month in range(1, 13):
            periodo = f"{year}{month:02d}"
            print(f"\n▶ Periodo {periodo}")

            for fondo_key in FONDOS:
                print(f"   → {FONDOS[fondo_key]} ({fondo_key})", end=" ")

                try:
                    csv = _descargar_fondo(periodo, fondo_key, session)
                    if csv:
                        print("✅")
                        if append:
                            dfs.append(pd.read_csv(csv))
                    else:
                        print("⚠️ sin datos")
                except Exception as e:
                    print(f"❌ error: {e}")

    if append and dfs:
        df_all = pd.concat(dfs, ignore_index=True)
        out = f"{CSV_AGREGADO_DIR}/{output}"
        df_all.to_csv(out, index=False)
        print(f"\n📦 CSV agregado generado: {out}")