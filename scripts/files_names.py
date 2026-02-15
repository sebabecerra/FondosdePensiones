from pathlib import Path
import json

ruta = Path("/Users/sbc/projects/FondosdePensiones/")

salida = ruta / "lista_archivos_csv.json"

def exportar_json(ruta):

    nombres = [
        f.stem
        for f in ruta.glob("*.csv")
        if f.stat().st_size > 0
    ]

    nombres.sort()

    with open(salida, "w", encoding="utf-8") as f:
        json.dump(nombres, f, indent=4, ensure_ascii=False)

    print(f"✅ JSON creado en: {salida}")
    print(f"📊 Total archivos: {len(nombres)}")

exportar_json(ruta)