import logging
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from src.enrutamiento import (
    RESPUESTA_ERROR,
    RESPUESTA_GENERICA,
    construir_cadena_con_enrutamiento,
    construir_cadena_queja_segura,
    construir_paso_clasificacion,
    procesar_mensaje_seguro,
)


def fallar_a_proposito(datos):
    # Simula un fallo del modelo sin hacer una petición real.
    raise ConnectionError("simulado")


def test_clasificacion_normaliza_antes_de_comparar():
    modelo_falso = MagicMock()
    modelo_falso.return_value = AIMessage(content=" Queja \n")

    resultado = construir_paso_clasificacion(modelo_falso).invoke({"mensaje": "Fonasa no me responde"})

    assert resultado == "queja"


def test_cadena_queja_usa_fallback_ante_fallo_del_modelo():
    # RunnableLambda real que falla: con un MagicMock genérico el fallback podría no ejecutarse.
    cadena_queja_segura = construir_cadena_queja_segura(RunnableLambda(fallar_a_proposito))

    resultado = cadena_queja_segura.invoke({"mensaje": "nadie me responde"})

    # Confirma que respondió el fallback, no solo que no hubo excepción.
    assert resultado == RESPUESTA_GENERICA
    assert "equipo" in resultado.lower()


def test_flujo_completo_usa_fallback_de_queja_sin_afectar_la_clasificacion():
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.return_value = "queja"

    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
        cadena_queja=construir_cadena_queja_segura(RunnableLambda(fallar_a_proposito)),
    )

    resultado = procesar_mensaje_seguro(cadena, "Llevo semanas esperando mi tramo")

    # La ruta falló, pero su fallback respondió antes de llegar al try/except general.
    assert resultado == RESPUESTA_GENERICA


def test_procesar_mensaje_seguro_no_propaga_excepciones(caplog):
    # side_effect hace que el mock lance la excepción, como una llamada real que falla.
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.side_effect = ConnectionError("simulado")

    cadena_falsa = construir_cadena_con_enrutamiento(paso_clasificacion=clasificacion_falsa)

    with caplog.at_level(logging.ERROR, logger="src.enrutamiento"):
        resultado = procesar_mensaje_seguro(cadena_falsa, "mensaje de prueba")

    # Un fallo fuera de las rutas solo lo cubre el try/except general.
    assert resultado == RESPUESTA_ERROR
    assert "no pudimos procesar" in resultado.lower()

    # El error queda registrado, no oculto.
    assert "Error procesando mensaje" in caplog.text
    assert "simulado" in caplog.text
