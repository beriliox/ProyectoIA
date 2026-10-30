from unittest.mock import patch

import pytest

from app.orientador import orientar

RESPUESTA_VALIDA = (
    '{"respuesta_directa": "El tramo se asigna según ingreso.", "requiere_tramite_presencial": false, '
    '"nivel_urgencia": "Bajo", "instituciones_involucradas": ["Fonasa"]}'
)


def test_orientar_devuelve_dict_validado():
    with patch("app.orientador.consultar_modelo", return_value=RESPUESTA_VALIDA) as mock_modelo:
        resultado = orientar("¿Qué tramo de Fonasa me corresponde?")
    assert resultado["instituciones_involucradas"] == ["Fonasa"]
    # se envía el schema para forzar JSON estructurado
    assert mock_modelo.call_args.args[2]["type"] == "OBJECT"


def test_orientar_rechaza_respuesta_incompleta():
    with patch("app.orientador.consultar_modelo", return_value='{"respuesta_directa": "x"}'):
        with pytest.raises(ValueError):
            orientar("¿Qué tramo de Fonasa me corresponde?")
