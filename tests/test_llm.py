from unittest.mock import patch, Mock

import pytest

from app import llm


@pytest.fixture(autouse=True)
def reiniciar_costo_total():
    llm.costo_total_sesion = 0
    yield


def respuesta_falsa(status_code, headers=None, json_data=None):
    respuesta = Mock(status_code=status_code, headers=headers or {})
    respuesta.json.return_value = json_data or {}
    return respuesta


def test_armar_peticion_rechaza_pregunta_vacia():
    with pytest.raises(ValueError):
        llm.armar_peticion("   ")


def test_armar_peticion_usa_modelo_unico_y_schema():
    url, body = llm.armar_peticion("hola", response_schema={"type": "OBJECT"})
    assert llm.MODELO in url
    assert body["generationConfig"]["responseMimeType"] == "application/json"


def test_enviar_peticion_credencial_invalida():
    with patch("app.llm.requests.post", return_value=respuesta_falsa(401)):
        with pytest.raises(ValueError):
            llm.enviar_peticion("https://ejemplo.invalid", {})


def test_enviar_peticion_429_corto_es_reintentable():
    with patch("app.llm.requests.post", return_value=respuesta_falsa(429, {"Retry-After": "5"})):
        with pytest.raises(TimeoutError):
            llm.enviar_peticion("https://ejemplo.invalid", {})


def test_enviar_peticion_cuota_diaria_falla_sin_reintentar():
    cuerpo = {"error": {"details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "7900s"}]}}
    with patch("app.llm.requests.post", return_value=respuesta_falsa(429, json_data=cuerpo)):
        with pytest.raises(RuntimeError, match="Cuota agotada"):
            llm.enviar_peticion("https://ejemplo.invalid", {})


def test_parsear_respuesta_json_quita_bloque_markdown():
    assert llm.parsear_respuesta_json('```json\n{"a": 1}\n```', ["a"]) == {"a": 1}


def test_parsear_respuesta_json_detecta_claves_faltantes():
    with pytest.raises(ValueError):
        llm.parsear_respuesta_json('{"a": 1}', ["a", "b"])


def test_con_reintento_no_reintenta_value_error():
    funcion = Mock(side_effect=ValueError("credencial inválida"))
    with patch("app.llm.time.sleep") as mock_sleep:
        with pytest.raises(ValueError):
            llm.con_reintento(funcion)
    funcion.assert_called_once()
    mock_sleep.assert_not_called()


def test_con_reintento_recupera_tras_un_fallo():
    funcion = Mock(side_effect=[TimeoutError("simulado"), "ok"])
    with patch("app.llm.time.sleep"):
        assert llm.con_reintento(funcion) == "ok"
    assert funcion.call_count == 2


def test_registrar_costo_acumula():
    llm.registrar_costo({"usageMetadata": {"totalTokenCount": 1000}})
    llm.registrar_costo({"usageMetadata": {"totalTokenCount": 1000}})
    assert llm.costo_total_sesion == pytest.approx(2 * llm.COSTO_POR_1000_TOKENS)


def test_consultar_modelo_convierte_timeout_en_runtime_error():
    with patch("app.llm.con_reintento", side_effect=TimeoutError("simulado")):
        with pytest.raises(RuntimeError):
            llm.consultar_modelo("pregunta de prueba")
