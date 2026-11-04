from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.peticiones import atender, construir_atencion, construir_clasificador


def ruta(nombre):
    return RunnableLambda(lambda _datos: nombre)


def atencion_con(intencion):
    return construir_atencion(RunnableLambda(lambda _: intencion), ruta("normativa"), ruta("reporte"), ruta("conversacional"))


@pytest.mark.parametrize("intencion", ["normativa", "reporte", "conversacional"])
def test_cada_intencion_va_a_su_ruta(intencion):
    resultado = atender("hola", atencion_con(intencion))
    assert resultado == {"consulta": "hola", "intencion": intencion, "respuesta": intencion}


def test_intencion_desconocida_va_a_conversacional():
    assert atender("hola", atencion_con("otra"))["respuesta"] == "conversacional"


def test_clasificador_normaliza_la_respuesta_del_modelo():
    modelo = MagicMock(return_value=AIMessage(content="  Normativa.\n"))
    assert construir_clasificador(modelo).invoke({"consulta": "¿Qué es el tramo A?"}) == "normativa"


def test_rechaza_consulta_vacia():
    with pytest.raises(ValueError):
        atender("   ", atencion_con("normativa"))
