"""
Utilidades para generación de períodos YYYYMM.
"""

def generar_periodos_anuales(desde: int, hasta: int):
    for anio in range(desde, hasta + 1):
        for mes in range(1, 13):
            yield f"{anio}{mes:02d}"


def generar_periodos_mensuales(desde: str, hasta: str):
    """
    desde, hasta en formato YYYYMM
    """
    anio_i, mes_i = int(desde[:4]), int(desde[4:])
    anio_f, mes_f = int(hasta[:4]), int(hasta[4:])

    anio, mes = anio_i, mes_i
    while (anio < anio_f) or (anio == anio_f and mes <= mes_f):
        yield f"{anio}{mes:02d}"
        mes += 1
        if mes == 13:
            mes = 1
            anio += 1
