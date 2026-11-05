from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from app.cadenas import construir_cadena_normativa


def correr_normativa():
    modelo_falso = MagicMock(side_effect=[
        AIMessage(content="Persona cesante en tramo C que quiere dejar de pagar."),
        AIMessage(content="Puedes pedir el cambio al tramo A en una sucursal de Fonasa."),
        AIMessage(content="Puedes pedir el cambio al tramo A [VERIFICAR] en una sucursal de Fonasa."),
    ])
    resultado = construir_cadena_normativa(modelo_falso).invoke({"consulta": "Perdí mi trabajo, ¿puedo cambiar de tramo?"})
    prompts = [llamada.args[0].to_string() for llamada in modelo_falso.call_args_list]
    return resultado, prompts


def test_normativa_ejecuta_los_tres_pasos_y_marca_cifras():
    resultado, prompts = correr_normativa()
    assert len(prompts) == 3
    assert "[VERIFICAR]" in resultado


def test_normativa_pasa_la_salida_de_cada_paso_al_siguiente():
    _, (extraer, redactar, revisar) = correr_normativa()
    assert "Perdí mi trabajo" in extraer
    assert "Persona cesante en tramo C" in redactar
    assert "sucursal de Fonasa" in revisar
