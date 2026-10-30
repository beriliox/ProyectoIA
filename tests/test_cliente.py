from unittest.mock import patch, Mock

import pytest

from src import cliente
from src.consumir_gemini import enviar_peticion


@pytest.fixture(autouse=True)
def reiniciar_costo_total():
    cliente.costo_total_sesion = 0
    yield

def test_enviar_peticion_credencial_invalida():
    respuesta_falsa = Mock(status_code=401)

    with patch("src.consumir_gemini.requests.post", return_value=respuesta_falsa):
        with pytest.raises(ValueError):
            enviar_peticion("https://ejemplo.invalid", {"pregunta": "test"})

def test_enviar_peticion_limite_de_uso():
    respuesta_falsa = Mock(status_code=429)

    with patch("src.consumir_gemini.requests.post", return_value=respuesta_falsa):
        with pytest.raises(TimeoutError):
            enviar_peticion("https://ejemplo.invalid", {"pregunta": "test"})

def test_enviar_peticion_exito():
    respuesta_falsa = Mock(status_code=200)
    respuesta_falsa.json.return_value = {"texto": "respuesta simulada"}

    with patch("src.consumir_gemini.requests.post", return_value=respuesta_falsa):
        resultado = enviar_peticion("https://ejemplo.invalid", {"pregunta": "test"})

    assert resultado == {"texto": "respuesta simulada"}


# con_reintento

def test_con_reintento_no_reintenta_value_error():
    funcion = Mock(side_effect=ValueError("credencial inválida"))

    with patch("src.cliente.time.sleep") as mock_sleep:
        with pytest.raises(ValueError):
            cliente.con_reintento(funcion)

    funcion.assert_called_once()
    mock_sleep.assert_not_called()

def test_con_reintento_agota_intentos():
    def siempre_falla():
        raise TimeoutError("simulado")
    
    with patch("src.cliente.time.sleep"):
        with pytest.raises(TimeoutError):
          cliente.con_reintento(siempre_falla, intentos=3)


# registrar_costo

def test_registrar_costo_acumula():
    respuesta_falsa = {"usageMetadata": 
        {
        "totalTokenCount": 1000
        }
    }
    
    costo = cliente.registrar_costo(respuesta_falsa)
    
    assert costo == cliente.COSTO_POR_1000_TOKENS
    assert cliente.costo_total_sesion == cliente.COSTO_POR_1000_TOKENS

# consultar_modelo

def test_consultar_modelo_convierte_error():
    error_simulado = TimeoutError("simulado")

    with patch("src.cliente.con_reintento", side_effect=error_simulado):
        with pytest.raises(RuntimeError):
            cliente.consultar_modelo("pregunta de prueba")