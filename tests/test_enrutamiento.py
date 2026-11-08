from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from src.enrutamiento import (
    construir_cadena_con_enrutamiento,
    construir_paso_clasificacion,
)


def test_enrutamiento_va_a_cadena_queja():
    # Se mockea la clasificación completa para forzar la ruta, sin llamar al modelo.
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.return_value = "queja"
    cadena_queja_falsa = MagicMock()
    cadena_queja_falsa.return_value = "respuesta de queja"

    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
        cadena_queja=cadena_queja_falsa,
    )
    resultado = cadena.invoke({"mensaje": "Llevo semanas esperando que Fonasa actualice mi tramo"})

    assert cadena_queja_falsa.called
    assert resultado == "respuesta de queja"


def test_enrutamiento_va_a_cadena_sugerencia():
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.return_value = "sugerencia"
    cadena_sugerencia_falsa = MagicMock()
    cadena_sugerencia_falsa.return_value = "respuesta de sugerencia"

    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
        cadena_sugerencia=cadena_sugerencia_falsa,
    )
    resultado = cadena.invoke({"mensaje": "Sería útil que me recordaran los documentos"})

    assert cadena_sugerencia_falsa.called
    assert resultado == "respuesta de sugerencia"


def test_enrutamiento_va_a_cadena_pregunta():
    # "pregunta" no tiene condición propia: llega a la ruta por defecto.
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.return_value = "pregunta"
    cadena_pregunta_falsa = MagicMock()
    cadena_pregunta_falsa.return_value = "respuesta de pregunta"

    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
        cadena_pregunta=cadena_pregunta_falsa,
    )
    resultado = cadena.invoke({"mensaje": "¿Qué necesito para actualizar mi Registro Social de Hogares?"})

    assert cadena_pregunta_falsa.called
    assert resultado == "respuesta de pregunta"


def test_enrutamiento_usa_default_ante_categoria_desconocida():
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.return_value = "categoria_inventada"
    cadena_pregunta_falsa = MagicMock()
    cadena_pregunta_falsa.return_value = "respuesta por defecto"

    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
        cadena_pregunta=cadena_pregunta_falsa,
    )
    cadena.invoke({"mensaje": "mensaje ambiguo"})

    assert cadena_pregunta_falsa.called


def test_clasificacion_normaliza_antes_de_comparar():
    # AIMessage real: StrOutputParser necesita un mensaje genuino para leer .content.
    modelo_falso = MagicMock()
    modelo_falso.return_value = AIMessage(content=" Queja \n")

    resultado = construir_paso_clasificacion(modelo_falso).invoke({"mensaje": "Fonasa no me responde"})

    assert resultado == "queja"
