"""Capa de respuesta: une prompt, modelo y validación. Es lo que FastAPI expondrá en el M3."""
from app.llm import consultar_modelo, parsear_respuesta_json
from app.prompts import ORIENTACION


def orientar(consulta: str) -> dict:
    texto = consultar_modelo(consulta, ORIENTACION["system_instruction"], ORIENTACION["response_schema"])
    return parsear_respuesta_json(texto, ORIENTACION["response_schema"]["required"])
