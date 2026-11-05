from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.cadenas import construir_clasificador
from app.peticiones import RESPALDO_CONVERSACIONAL, RESPALDO_NORMATIVA, RESPUESTA_ERROR, atender, construir_atencion


def ruta(nombre):
    return RunnableLambda(lambda _datos: nombre)


def atencion_con(intencion):
    return construir_atencion(RunnableLambda(lambda _: intencion), ruta("normativa"), ruta("conversacional"))


def test_clasificacion_normaliza_antes_de_comparar():
    modelo_falso = MagicMock(return_value=AIMessage(content="  Normativa.\n"))
    assert construir_clasificador(modelo_falso).invoke({"consulta": "¿Qué es el tramo A?"}) == "normativa"


@pytest.mark.parametrize("intencion", ["normativa", "conversacional"])
def test_enrutamiento_va_a_la_ruta_de_su_intencion(intencion):
    resultado = atender("hola", atencion_con(intencion))
    assert resultado == {"consulta": "hola", "intencion": intencion, "respuesta": intencion}


def test_enrutamiento_usa_conversacional_ante_intencion_desconocida():
    assert atender("hola", atencion_con("otra"))["respuesta"] == "conversacional"


def test_rechaza_consulta_vacia():
    with pytest.raises(ValueError):
        atender("   ", atencion_con("normativa"))


def fallar_a_proposito(_datos):
    raise ConnectionError("simulado")


def test_ruta_normativa_usa_respaldo_ante_fallo_del_modelo():
    atencion = construir_atencion(
        RunnableLambda(lambda _: "normativa"), RunnableLambda(fallar_a_proposito), ruta("conversacional")
    )
    assert atender("¿Qué es el tramo A?", atencion)["respuesta"] == RESPALDO_NORMATIVA


def test_ruta_conversacional_usa_respaldo_ante_fallo_del_modelo():
    atencion = construir_atencion(
        RunnableLambda(lambda _: "conversacional"), ruta("normativa"), RunnableLambda(fallar_a_proposito)
    )
    assert atender("hola", atencion)["respuesta"] == RESPALDO_CONVERSACIONAL


def test_atender_no_propaga_excepciones_si_falla_la_clasificacion():
    clasificacion_falsa = MagicMock(side_effect=ConnectionError("simulado"))
    atencion = construir_atencion(clasificacion_falsa, ruta("normativa"), ruta("conversacional"))
    resultado = atender("hola", atencion)
    assert resultado["intencion"] == "error"
    assert resultado["respuesta"] == RESPUESTA_ERROR
