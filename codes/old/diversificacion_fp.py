import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from urllib.parse import urljoin
from typing import List, Optional

# =================================================
# CONFIG
# =================================================
BASE_URL = "https://www.spensiones.cl"

HTML_DIR = "data/reporte_3/html/mensual"
CSV_DIR  = "data/reporte_3/csv/mensual"
CSV_AGR  = "data/reporte_3/csv/agregado"

os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(CSV_AGR, exist_ok=True)

# 🔑 FIRMA DEL REPORTE 3 (parte estable del param)
# (la que tú identificaste en el HTML)
PARAM_FIRMA_REPORTE_3 = "bXZjVVJiNkE4cEpN"

# =================================================
# HELPERS (IGUALES A carteras_fp.py)
# =================================================
def _crear_sesion() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{BASE_URL}/apps/centroEstadisticas/paginaCuadrosCCEE.php",
    })
    return s


def _generar_periodos(desde: int, hasta: int) -> List[str]:
    return [
        f"{y}{str(m).zfill(2)}"
        for y in range(desde, hasta + 1)
        for m in range(1, 13)
    ]


# =================================================
# CORE (MISMA LÓGICA)
# =================================================
def _procesar_periodo(periodo: str, session: requests.Session) -> Optional[str]:

    # 1️⃣ Página intermedia (IGUAL)
    url = (
        f"{BASE_URL}/apps/loadCarteras/loadCarAgr.php"
        f"?menu=sci&menuN1=estfinfp&menuN2=NOID"
        f"&orden=20&periodo={periodo}&ext=.php"
    )

    resp = session.get(url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # 2️⃣ Buscar el link (MISMO for, distinta condición)
    link = None
    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "genera_xsl_v2.0.php" not in href:
            continue

        # 🔑 condición que identifica el REPORTE 3
        if PARAM_FIRMA_REPORTE_3 in href:
            link = urljoin(BASE_URL, href)
            break

    if not link:
        return None

    # 3️⃣ Descargar HTML final (IGUAL)
    html_resp = session.get(link, timeout=60)
    html_resp.raise_for_status()

    html_text = (
        html_resp.content
        .decode("utf-8", errors="ignore")
        .replace(".", "")
        .replace(",", ".")
    )

    html_path = f"{HTML_DIR}/reporte_3_{periodo}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_text)

    # 4️⃣ Parse (ajusta si el reporte tiene otra estructura)
    df = pd.read_html(html_path)[0]
    df = df.dropna(how="all").reset_index(drop=True)

    df["PERIODO"] = periodo

    out_csv = f"{CSV_DIR}/reporte_3_{periodo}.csv"
    df.to_csv(out_csv, index=False)

    return out_csv


# =================================================
# FUNCIÓN PÚBLICA (IGUAL)
# =================================================
def descargar_reporte_3_fp(
    desde: int,
    hasta: int,
    append: bool = False,
    output: str = "reporte_3_total.csv"
) -> None:

    session = _crear_sesion()
    periodos = _generar_periodos(desde, hasta)

    dfs = []

    for p in periodos:
        print(f"▶ Procesando reporte 3 {p}", end=" ")
        try:
            csv = _procesar_periodo(p, session)
            if csv:
                print("✅")
                if append:
                    dfs.append(pd.read_csv(csv))
            else:
                print("⚠️ sin datos")
        except Exception as e:
            print(f"❌ {e}")

    if append and dfs:
        df_all = pd.concat(dfs, ignore_index=True)
        out = f"{CSV_AGR}/{output}"
        df_all.to_csv(out, index=False)
        print(f"\n📦 CSV agregado generado: {out}")


descargar_reporte_3_fp(2025, 2025, append=True)
