import pytest

import src.agente_tramites as agente


@pytest.fixture(autouse=True)
def estado_limpio():
    agente.registro_aprobaciones.clear()
    agente.solicitudes_enviadas.clear()
    agente.notas_hogar.clear()


def test_solicitud_rechazada_no_se_envia_pero_queda_registrada(monkeypatch):
    monkeypatch.setattr(agente, "esperar_aprobacion", lambda mensaje: False)

    respuesta = agente.enviar_solicitud_actualizacion_rsh.invoke({"motivo": "cambio_domicilio"})

    assert "NO aprobada" in respuesta
    assert agente.solicitudes_enviadas == {}
    assert agente.registro_aprobaciones[0]["aprobado"] is False


def test_solicitud_aprobada_se_envia_una_sola_vez(monkeypatch):
    preguntas = []
    monkeypatch.setattr(agente, "esperar_aprobacion", lambda mensaje: preguntas.append(mensaje) or True)

    primera = agente.enviar_solicitud_actualizacion_rsh.invoke({"motivo": "cambio_ingresos"})
    segunda = agente.enviar_solicitud_actualizacion_rsh.invoke({"motivo": "cambio_ingresos"})

    assert "SIMULADA" in primera
    assert "No se repite" in segunda
    assert len(preguntas) == 1  #el duplicado no vuelve a pedir aprobación


def test_sin_consola_no_se_aprueba(monkeypatch):
    monkeypatch.setattr(agente.sys.stdin, "isatty", lambda: False)
    assert agente.esperar_aprobacion("¿Aprobar?") is False


def test_nota_se_corrige_reescribiendo_sin_pedir_aprobacion(monkeypatch):
    monkeypatch.setattr(agente, "esperar_aprobacion", lambda mensaje: pytest.fail("no debe pedir aprobación"))

    agente.guardar_nota_hogar.invoke({"tema": "domicilio", "nota": "cambio hace un mes"})
    respuesta = agente.guardar_nota_hogar.invoke({"tema": "domicilio", "nota": "cambio hace dos meses"})

    assert agente.notas_hogar == {"domicilio": "cambio hace dos meses"}
    assert "cambio hace un mes" in respuesta  #el valor anterior queda en la traza


def test_nota_con_rut_se_rechaza():
    with pytest.raises(Exception):
        agente.guardar_nota_hogar.invoke({"tema": "otro", "nota": "mi rut es 12.345.678-9"})
    assert agente.notas_hogar == {}
