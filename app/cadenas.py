"""Capa 2, cadenas: cómo la app conversa con el modelo. Cada función recibe el modelo
como parámetro para poder probarla con un modelo falso (base: ejemplos/cadena_tres_pasos.py).
"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app import prompts


def paso(plantilla: str, modelo):
    return PromptTemplate.from_template(plantilla) | modelo | StrOutputParser()


def construir_cadena_normativa(modelo):
    """extraer situación → redactar orientación → revisar y marcar cifras con [VERIFICAR]."""
    return (
        paso(prompts.EXTRAER_SITUACION, modelo)
        | (lambda situacion: {"situacion": situacion})
        | paso(prompts.REDACTAR_ORIENTACION, modelo)
        | (lambda borrador: {"borrador": borrador})
        | paso(prompts.REVISAR_ORIENTACION, modelo)
    )
