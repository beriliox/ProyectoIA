import pytest

from app.procesamiento import procesar_texto
from app.evaluacion import calcular_metricas, resumir_metricas


def test_procesar_texto_normaliza_mayusculas_y_puntuacion():
    assert procesar_texto("¿Qué es el Tramo B de FONASA?") == ["qué", "es", "el", "tramo", "b", "de", "fonasa"]


def test_procesar_texto_solo_puntuacion_devuelve_lista_vacia():
    assert procesar_texto("¡¡¡...!!!") == []


def test_procesar_texto_rechaza_no_texto():
    with pytest.raises(TypeError):
        procesar_texto(None)


def test_calcular_metricas_respuesta_identica():
    assert calcular_metricas("Fonasa tramo A", "fonasa, tramo A.") == {"precision": 1.0, "cobertura": 1.0, "f1": 1.0}


def test_calcular_metricas_parcial():
    # referencia 4 tokens, respuesta 2 tokens, 2 coincidencias
    metricas = calcular_metricas("el tramo a cubre", "tramo a")
    assert metricas["precision"] == 1.0
    assert metricas["cobertura"] == 0.5
    assert metricas["f1"] == pytest.approx(2 / 3)


def test_calcular_metricas_sin_coincidencias_o_vacia():
    assert calcular_metricas("fonasa", "rsh")["f1"] == 0.0
    assert calcular_metricas("fonasa", "")["f1"] == 0.0


def test_resumir_metricas_lista_vacia():
    assert resumir_metricas([]) == {"precision_promedio": 0, "cobertura_promedio": 0, "f1_promedio": 0}
