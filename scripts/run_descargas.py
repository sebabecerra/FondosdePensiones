from fondosdepensiones.carteras_inversion_agregadas import descargar_carteras_rango
from fondosdepensiones.eeff import descargar_eeff_rango

def main():
    descargar_carteras_rango(2024, 2025)
    descargar_eeff_rango(2024, 2025)

if __name__ == "__main__":
    main()
