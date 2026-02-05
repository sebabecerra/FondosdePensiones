from codes.old.carteras_fp_por_afp import descargar_carteras_por_fondo

def main():
    print("Descarga Carteras por Fondo AFP\n")

    desde = int(input("Año inicio (ej: 2008): "))
    hasta = int(input("Año fin    (ej: 2012): "))

    resp = input("¿Agregar todo en un solo CSV? (s/n): ").lower()
    append = resp == "s"

    descargar_carteras_por_fondo(
        desde,
        hasta,
        append=append,
        output=f"carteras_fondos_{desde}_{hasta}.csv"
    )

if __name__ == "__main__":
    main()

