"""
Auditoría Anual de Integridad 1:1 – fondosdepensiones

Este script analiza un año completo, comparando mes a mes la cantidad de 
links oficiales (X) contra los archivos CSV (Y) descargados.
"""

import os
import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime

# --- INYECCIÓN DE RUTA PARA IMPORTAR DESDE SRC ---
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(os.path.join(BASE_DIR, "src"))

try:
    from fondosdepensiones.session import crear_sesion
    from fondosdepensiones.config import DATA_DIR, BASE_URL
except ImportError:
    print("❌ ERROR: No se pudo importar la configuración. Ejecuta desde la raíz.")
    sys.exit(1)

# --- MAPA DE CONFIGURACIÓN TÉCNICA ---
CONFIG_AUDITORIA = {
    "1": {
        "nombre": "Carteras Inversión Agregadas",
        "carpeta": "Carteras_Inversiones_agregadas",
        "url_fmt": "{base}/apps/loadCarteras/loadCarAgr.php?menu=sci&menuN1=estfinfp&menuN2=NOID&orden=20&periodo={periodo}&ext=.php",
        "filtro_link": "genera_xsl_v2.0.php"
    },
    "2": {
        "nombre": "Carteras Inversión (Desagregadas)",
        "carpeta": "Carteras_Inversiones",
        "url_fmt": "{base}/apps/loadCarteras/loadCarInv.php?menu=sci&menuN1=estfinfp&menuN2=NOID&orden=10&periodo={periodo}&ext=.php",
        "filtro_link": "genera_desagregada_xsl_v2.0.php"
    },
    "3": {
        "nombre": "Estados Financieros (EEFF)",
        "carpeta": "Estados_Financieros",
        "url_fmt": "{base}/apps/loadEstadisticas/loadFecuFondo.php?menu=sci&menuN1=estfinfp&menuN2=NOID&orden=30&periodo={periodo}&ext=.php",
        "filtro_link": "loadCuadroFecuFondo.php"
    }
}

def auditar_anio(opcion, anio):
    conf = CONFIG_AUDITORIA[opcion]
    session = crear_sesion()
    hoy = datetime.now()

    print(f"\n" + "="*95)
    print(f"📊 REPORTE ANUAL DE INTEGRIDAD: {conf['nombre']}")
    print(f"📅 AÑO: {anio} | Ruta: data/{conf['carpeta']}/{anio}")
    print("="*95)
    print(f"{'PERIODO':<12} | {'WEB (X)':<10} | {'DISCO (Y)':<10} | {'ESTADO':<15} | {'DETALLE'}")
    print("-" * 95)

    total_web_anio = 0
    total_disco_anio = 0

    for mes in range(1, 13):
        periodo = f"{anio}{mes:02d}"
        
        # No auditar meses que aún no han ocurrido
        if int(periodo) > int(hoy.strftime("%Y%m")):
            break

        # 1. Obtener Verdad de la Web
        url_objetivo = conf["url_fmt"].format(base=BASE_URL, periodo=periodo)
        try:
            resp = session.get(url_objetivo, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            links_web = [a["href"] for a in soup.find_all("a", href=True) if conf["filtro_link"] in a["href"]]
            if opcion == "3": # Filtro extra para EEFF
                links_web = [l for l in links_web if "tipo=html" in l]
            
            n_web = len(links_web)
        except Exception:
            n_web = 0 # Asumimos no publicado o error temporal

        # 2. Obtener Realidad del Disco
        ruta_local = DATA_DIR / conf["carpeta"] / str(anio) / "csv" / periodo
        n_disco = len(list(ruta_local.glob("*.csv"))) if ruta_local.exists() else 0

        # 3. Lógica de Estado
        if n_web == 0:
            estado = "⚪ VACÍO WEB"
            detalle = "Sin links en SPensiones"
        elif n_web == n_disco:
            estado = "✅ OK"
            detalle = "Sincronizado"
        elif n_disco == 0:
            estado = "❌ FALTANTE"
            detalle = f"Faltan los {n_web} cuadros"
        else:
            estado = "⚠️  INCOMPLETO"
            detalle = f"Faltan {n_web - n_disco} cuadros"

        print(f"{periodo:<12} | {n_web:<10} | {n_disco:<10} | {estado:<15} | {detalle}")
        
        total_web_anio += n_web
        total_disco_anio += n_disco

    print("-" * 95)
    print(f"{'TOTALES':<12} | {total_web_anio:<10} | {total_disco_anio:<10} | "
          f"{'COMPLETITUD:':<15} {((total_disco_anio/total_web_anio)*100 if total_web_anio > 0 else 0):.1f}%")
    print("=" * 95)

def main():
    print("\n--- SISTEMA DE AUDITORÍA ANUAL 1:1 ---")
    print("1. Carteras Inversión Agregadas")
    print("2. Carteras Inversión (Desagregadas)")
    print("3. Estados Financieros (EEFF)")
    
    op = input("\nDataset a auditar [1-3]: ")
    if op not in CONFIG_AUDITORIA: return
    
    anio = input("Año a auditar (YYYY): ")
    if not anio.isdigit() or len(anio) != 4:
        print("Año inválido.")
        return

    auditar_anio(op, anio)

if __name__ == "__main__":
    main()