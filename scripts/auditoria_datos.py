"""
Auditoría Anual de Integridad 1:1 – fondosdepensiones (Google-style / production-grade)

OBJETIVO
--------
Auditar un año completo, mes a mes, comparando:

SALIDA 1 (TABLA):
    WEB (X)  = # de links oficiales encontrados en SPensiones para ese periodo (fuente de verdad "publicada")
    DISCO(Y) = # de CSV realmente presentes en el disco para ese periodo (fuente de verdad "descargada")

SALIDA 2 (DETALLE):
    Al FINAL del reporte, para cada mes incompleto:
        listar los nombres exactos de los cuadros faltantes (con ❌),
        comparando nombres del DISCO contra el universo esperado definido en:
            lista_archivos_csv.json

IMPORTANTE (por diseño)
-----------------------
- WEB (X) SIEMPRE se obtiene desde la web (SPensiones) vía HTML.
  -> Esto responde: "¿Cuántos cuadros publicó oficialmente SPensiones en este mes?"
- El JSON NO se usa para calcular WEB (X).
  -> El JSON es un "catálogo estructural" de nombres esperados (Z) para comparar contra DISCO.
- DISCO (Y) se obtiene leyendo el filesystem (glob *.csv).

Modelo:
    X_t = |links publicados en web para periodo t|
    Y_t = |csv descargados en disco para periodo t|
    Z   = conjunto de nombres esperados (catálogo) cargado desde JSON

Auditoría integridad (tabla):
    X_t vs Y_t

Forense de nombres (detalle):
    faltantes_t = Z - nombres_disco_t

Requisitos para que el detalle sea correcto:
--------------------------------------------
- lista_archivos_csv.json debe contener EXACTAMENTE los "stems" (nombre sin .csv)
  que tu descargador produce (misma normalización / limpiar_nombre).
- Los archivos en disco deben tener el mismo stem.

Autor: SBC”
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

import requests
from bs4 import BeautifulSoup

# =============================================================================
# Bootstrap para importar módulos internos del proyecto (src/)
# =============================================================================
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(os.path.join(BASE_DIR, "src"))

try:
    from fondosdepensiones.session import crear_sesion
    from fondosdepensiones.config import DATA_DIR, BASE_URL
except ImportError:
    print("❌ ERROR: No se pudo importar la configuración. Ejecuta desde la raíz del repo.")
    sys.exit(1)

# =============================================================================
# Configuración (MISMA estructura que tu auditoría original)
# =============================================================================
CONFIG_AUDITORIA = {
    "1": {
        "nombre": "Carteras Inversión Agregadas",
        "carpeta": "Carteras_Inversiones_agregadas",
        "url_fmt": (
            "{base}/apps/loadCarteras/loadCarAgr.php?"
            "menu=sci&menuN1=estfinfp&menuN2=NOID&orden=20&periodo={periodo}&ext=.php"
        ),
        "filtro_link": "genera_xsl_v2.0.php",
    },
    "2": {
        "nombre": "Carteras Inversión (Desagregadas)",
        "carpeta": "Carteras_Inversiones",
        "url_fmt": (
            "{base}/apps/loadCarteras/loadCarInv.php?"
            "menu=sci&menuN1=estfinfp&menuN2=NOID&orden=10&periodo={periodo}&ext=.php"
        ),
        "filtro_link": "genera_desagregada_xsl_v2.0.php",
    },
    "3": {
        "nombre": "Estados Financieros (EEFF)",
        "carpeta": "Estados_Financieros",
        "url_fmt": (
            "{base}/apps/loadEstadisticas/loadFecuFondo.php?"
            "menu=sci&menuN1=estfinfp&menuN2=NOID&orden=30&periodo={periodo}&ext=.php"
        ),
        "filtro_link": "loadCuadroFecuFondo.php",
    },
}

# =============================================================================
# Helpers (Google-style: pequeñas funciones con propósito único)
# =============================================================================

def _cargar_catalogo_esperado(path_json: Path) -> Set[str]:
    """
    Carga el catálogo de nombres esperados desde JSON.

    Esperado:
        JSON = [ "stem1", "stem2", ... ]
        donde stem = nombre de archivo sin ".csv"

    Retorna:
        set(stems)
    """
    if not path_json.exists():
        raise FileNotFoundError(f"No existe el JSON esperado: {path_json}")

    with path_json.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Tu error anterior venía de acá: el JSON es LISTA, no diccionario por periodo.
    if not isinstance(data, list):
        raise ValueError("lista_archivos_csv.json debe ser una LISTA de strings.")

    # Validación suave: asegurar strings
    out: Set[str] = set()
    for x in data:
        if isinstance(x, str) and x.strip():
            out.add(x.strip())
    return out


def _contar_links_web(
    session: requests.Session,
    url_objetivo: str,
    filtro_link: str,
    es_eeff: bool,
    timeout: int = 20
) -> int:
    """
    Fuente de verdad WEB (X):
    - Baja el HTML del "menú mensual"
    - Cuenta <a href="..."> cuyo href contiene filtro_link.

    Caso EEFF:
    - además exige "tipo=html" en el href.
    """
    resp = session.get(url_objetivo, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    links = [
        a["href"]
        for a in soup.find_all("a", href=True)
        if filtro_link in a["href"]
    ]

    if es_eeff:
        links = [l for l in links if "tipo=html" in l]

    return len(links)


def _leer_stems_en_disco(ruta_local: Path) -> Set[str]:
    """
    Fuente de verdad DISCO (Y):
    - Lee *.csv dentro de ruta_local
    - Devuelve el set de stems (nombre sin extensión)

    Si la carpeta no existe -> set vacío.
    """
    if not ruta_local.exists():
        return set()
    return {p.stem for p in ruta_local.glob("*.csv")}


def _estado_y_detalle(n_web: int, n_disco: int) -> Tuple[str, str]:
    """
    Reproduce EXACTAMENTE la misma lógica semántica de tu auditoría original,
    con símbolos:

    - VACÍO WEB
    - OK
    - FALTANTE
    - INCOMPLETO

    Retorna:
        (estado, detalle)
    """
    if n_web == 0:
        return "⚪ VACÍO WEB", "Sin links en SPensiones"
    if n_web == n_disco:
        return "✅ OK", "Sincronizado"
    if n_disco == 0:
        return "❌ FALTANTE", f"Faltan los {n_web} cuadros"
    return "⚠️  INCOMPLETO", f"Faltan {n_web - n_disco} cuadros"


# =============================================================================
# Core
# =============================================================================

def auditar_anio(opcion: str, anio: str) -> None:
    """
    Ejecuta auditoría anual:
    SALIDA 1: tabla
    SALIDA 2: lista de nombres faltantes por mes incompleto
    """
    conf = CONFIG_AUDITORIA[opcion]
    session = crear_sesion()
    hoy = datetime.now()

    # Catalogo esperado (Z) – se usa SOLO para “nombres faltantes”
    catalogo_path = BASE_DIR / "lista_archivos_csv.json"
    nombres_esperados = _cargar_catalogo_esperado(catalogo_path)

    # Guardamos faltantes por mes para imprimirlos al final (SALIDA 2)
    faltantes_por_mes: Dict[str, List[str]] = {}

    # -----------------------------
    # SALIDA 1: Encabezado tabla
    # -----------------------------
    print("\n" + "=" * 95)
    print(f"📊 REPORTE ANUAL DE INTEGRIDAD: {conf['nombre']}")
    print(f"📅 AÑO: {anio} | Ruta: data/{conf['carpeta']}/{anio}")
    print("=" * 95)
    print(f"{'PERIODO':<12} | {'WEB (X)':<10} | {'DISCO (Y)':<10} | {'ESTADO':<15} | {'DETALLE'}")
    print("-" * 95)

    total_web_anio = 0
    total_disco_anio = 0

    # -----------------------------
    # Loop mensual
    # -----------------------------
    for mes in range(1, 13):
        periodo = f"{anio}{mes:02d}"

        # no auditar meses futuros
        if int(periodo) > int(hoy.strftime("%Y%m")):
            break

        # ===== WEB (X) =====
        url_objetivo = conf["url_fmt"].format(base=BASE_URL, periodo=periodo)
        try:
            n_web = _contar_links_web(
                session=session,
                url_objetivo=url_objetivo,
                filtro_link=conf["filtro_link"],
                es_eeff=(opcion == "3"),
            )
        except Exception:
            # Mantengo tu política original: si falla web, asumir 0.
            n_web = 0

        # ===== DISCO (Y) =====
        ruta_local = DATA_DIR / conf["carpeta"] / str(anio) / "csv" / periodo
        nombres_disco = _leer_stems_en_disco(ruta_local)
        n_disco = len(nombres_disco)

        # ===== ESTADO / DETALLE (tabla) =====
        estado, detalle = _estado_y_detalle(n_web, n_disco)

        # Si incompleto, calcular faltantes por nombres (Z - disco)
        # OJO: Esto asume que "nombres_esperados" aplica a todos los meses.
        # Si tu catálogo cambia por año o por dataset, deberías versionarlo.
        if estado.startswith("⚠️"):
            faltantes = sorted(nombres_esperados - nombres_disco)
            faltantes_por_mes[periodo] = faltantes

        print(f"{periodo:<12} | {n_web:<10} | {n_disco:<10} | {estado:<15} | {detalle}")

        total_web_anio += n_web
        total_disco_anio += n_disco

    # -----------------------------
    # Footer tabla
    # -----------------------------
    print("-" * 95)
    completitud = (total_disco_anio / total_web_anio * 100) if total_web_anio > 0 else 0.0
    print(
        f"{'TOTALES':<12} | {total_web_anio:<10} | {total_disco_anio:<10} | "
        f"{'COMPLETITUD:':<15} {completitud:.1f}%"
    )
    print("=" * 95)

    # =============================================================================
    # SALIDA 2: Detalle de nombres faltantes (solo al final)
    # =============================================================================
    if faltantes_por_mes:
        print("\n\nDETALLE DE CUADROS FALTANTES (comparación de nombres: JSON vs DISCO)")
        print("=" * 95)

        for periodo in sorted(faltantes_por_mes.keys()):
            faltantes = faltantes_por_mes[periodo]
            print(f"\n{periodo}  (faltan {len(faltantes)}):")
            for name in faltantes:
                print(f"  └─ ❌ {name}.csv")

def auditar_rango_anios(opcion: str, anio_inicio: str, anio_fin: str) -> None:
    """
    Orquestador multi-año.

    Ejecuta auditar_anio() para cada año en el rango cerrado:
        [anio_inicio, anio_fin]

    Ej:
        2018–2020 → 2018, 2019, 2020

    NO:
    - duplica lógica
    - modifica auditoría interna
    - altera modelo X vs Y vs Z

    Solo itera temporalmente.
    """

    try:
        y0 = int(anio_inicio)
        y1 = int(anio_fin)
    except ValueError:
        print("❌ Años deben ser numéricos")
        return

    if y0 > y1:
        print("❌ Año inicio mayor que año fin")
        return

    print("\n" + "#" * 110)
    print(f"🔎 AUDITORÍA MULTI-AÑO: {y0} → {y1}")
    print("#" * 110)

    for anio in range(y0, y1 + 1):
        auditar_anio(opcion, str(anio))

def main() -> None:
    print("\n--- SISTEMA DE AUDITORÍA ANUAL 1:1 ---")
    print("1. Carteras Inversión Agregadas")
    print("2. Carteras Inversión (Desagregadas)")
    print("3. Estados Financieros (EEFF)")

    op = input("\nDataset a auditar [1-3]: ").strip()
    if op not in CONFIG_AUDITORIA:
        return

    print("\nModo de auditoría:")
    print("1. Año único")
    print("2. Rango de años")

    modo = input("\nModo [1-2]: ").strip()

    if modo == "1":
        anio = input("Año a auditar (YYYY): ").strip()
        if not anio.isdigit() or len(anio) != 4:
            print("Año inválido.")
            return
        auditar_anio(op, anio)

    elif modo == "2":
        a0 = input("Año inicio (YYYY): ").strip()
        a1 = input("Año fin (YYYY): ").strip()

        if not (a0.isdigit() and a1.isdigit() and len(a0) == 4 and len(a1) == 4):
            print("Rango inválido.")
            return

        auditar_rango_anios(op, a0, a1)


if __name__ == "__main__":
    main()