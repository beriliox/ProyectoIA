import pytest

from app import modelo


def test_crear_modelo_sin_api_key_lanza_error(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    with pytest.raises(ValueError):
        modelo.crear_modelo()


def test_crear_modelo_usa_la_configuracion_del_proyecto(monkeypatch):
    monkeypatch.setenv("API_KEY", "llave-falsa")
    chat = modelo.crear_modelo(temperatura=0.7)
    assert chat.model.endswith(modelo.MODELO)
    assert chat.temperature == 0.7
    assert chat.timeout == modelo.TIMEOUT_SEGUNDOS
