import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.spensiones.cl"
PERIODO = "202401"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Referer": f"{BASE_URL}/apps/centroEstadisticas/paginaCuadrosCCEE.php",
})

# 1. Página intermedia
url = (
    f"{BASE_URL}/apps/loadCarteras/loadCarAgr.php"
    f"?menu=sci&menuN1=estfinfp&menuN2=NOID"
    f"&orden=20&periodo={PERIODO}&ext=.php"
)

html = session.get(url).text
soup = BeautifulSoup(html, "html.parser")

# 2. Buscar EXACTAMENTE el <a> que tú pegaste
link = None
for a in soup.find_all("a", title="Html", href=True):
    if "genera_xsl_v2.0.php" in a["href"]:
        # este print es CLAVE para depurar
        print("CANDIDATO:", a["href"])

        # el bueno es el que está bajo el texto correcto
        li = a.find_parent("li")
        if li and "Diversificación de instrumentos financieros" in li.get_text():
            link = urljoin(BASE_URL, a["href"])
            break

if not link:
    raise RuntimeError("No se encontró el link de diversificación")

print("LINK FINAL:", link)

# 3. Descargar
resp = session.get(link)
print("STATUS:", resp.status_code, "LENGTH:", len(resp.content))
