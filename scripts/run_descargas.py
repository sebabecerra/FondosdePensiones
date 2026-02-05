from fondosdepensiones.carteras import descargar_carteras_rango
from fondosdepensiones.fecu import descargar_fecu_rango

def main():
    descargar_carteras_rango(2024, 2025)
    descargar_fecu_rango(2024, 2025)

if __name__ == "__main__":
    main()
