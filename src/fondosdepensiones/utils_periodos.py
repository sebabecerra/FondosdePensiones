"""Módulo de Semántica Temporal para el Sistema de Pensiones.

Este módulo centraliza la 'Regla de Oro' de granularidad para cada tipo de dato:
- Carteras/Balance D1: Mensual (YYYYMM)
- EEFF: Trimestral (03, 06, 09, 12)
- Valores Cuota/Precios IF: Anual (YYYY)

La responsabilidad de este módulo es asegurar que las intenciones del usuario 
se traduzcan en periodos válidos para los endpoints de la Superintendencia.
"""

from typing import List, Generator


def meses_de_anio(anio: int) -> List[str]:
    """Expande un año en 12 meses (YYYY01..YYYY12)."""
    return [f"{anio}{m:02d}" for m in range(1, 13)]


def meses_de_rango(desde: int, hasta: int) -> List[str]:
    """Genera todos los meses entre dos años completos (inclusive)."""
    periodos: List[str] = []
    for anio in range(desde, hasta + 1):
        periodos.extend(meses_de_anio(anio))
    return periodos


def trimestres_de_anio(anio: int) -> List[str]:
    """Expande un año en sus 4 trimestres oficiales (03, 06, 09, 12)."""
    return [f"{anio}{m:02d}" for m in (3, 6, 9, 12)]


def trimestres_de_rango(desde: int, hasta: int) -> List[str]:
    """Genera hitos trimestrales para un rango de años."""
    periodos: List[str] = []
    for anio in range(desde, hasta + 1):
        periodos.extend(trimestres_de_anio(anio))
    return periodos


def es_trimestre_eeff(periodo_yyyymm: str) -> bool:
    """Valida si el mes pertenece a un cierre contable (Mar, Jun, Sep, Dic)."""
    if len(periodo_yyyymm) != 6 or not periodo_yyyymm.isdigit():
        return False
    mm = int(periodo_yyyymm[4:6])
    return mm in (3, 6, 9, 12)


def generar_periodos_mensuales(desde: str, hasta: str) -> Generator[str, None, None]:
    """Generador secuencial de meses entre dos puntos YYYYMM."""
    anio_i, mes_i = int(desde[:4]), int(desde[4:])
    anio_f, mes_f = int(hasta[:4]), int(hasta[4:])

    anio, mes = anio_i, mes_i
    while (anio < anio_f) or (anio == anio_f and mes <= mes_f):
        yield f"{anio}{mes:02d}"
        mes += 1
        if mes == 13:
            mes = 1
            anio += 1