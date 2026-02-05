# run_fp.py
from codes.old.carteras_fp import descargar_carteras_agregadas_FP

def main():
    print("Descarga de Carteras Agregadas AFP\n")

    desde = int(input("Año inicio (ej: 2003): "))
    hasta = int(input("Año fin    (ej: 2007): "))

    resp = input("¿Agregar todo en un solo CSV? (s/n): ").lower()
    append = resp == "s"

    descargar_carteras_agregadas_FP(
        desde,
        hasta,
        append=append,
        output=f"cartera_{desde}_{hasta}.csv"
    )

if __name__ == "__main__":
    main()