"""Capa 3, peticiones: clasifica la consulta y la deriva a una sola ruta (bloque 19).

    consulta ─► clasificar ─┬► normativa       → cadena de tres pasos
                            └► conversacional  → respuesta breve (ruta por defecto)

Base en los ejemplos: ejemplos/bifurcacion.py y ejemplos/enrutamiento.py.
Es lo que FastAPI expondrá en el Módulo 3.
"""
from langchain_core.runnables import RunnableBranch, RunnablePassthrough

from app.cadenas import construir_cadena_conversacional, construir_cadena_normativa, construir_clasificador


def construir_atencion(clasificador, ruta_normativa, ruta_conversacional):
    """Cada ruta recibe {"consulta", "intencion"} y devuelve el texto de la respuesta."""
    bifurcacion = RunnableBranch(
        (lambda datos: datos["intencion"] == "normativa", ruta_normativa),
        ruta_conversacional,  # por defecto: una clasificación rara nunca termina inventando normativa
    )
    return RunnablePassthrough.assign(intencion=clasificador) | RunnablePassthrough.assign(respuesta=bifurcacion)


def crear_atencion():
    from app.modelo import crear_modelo

    modelo = crear_modelo()
    return construir_atencion(
        construir_clasificador(modelo),
        construir_cadena_normativa(modelo),
        construir_cadena_conversacional(crear_modelo(temperatura=0.7)),
    )


def atender(consulta: str, atencion=None) -> dict:
    if not consulta or not consulta.strip():
        raise ValueError("La consulta no puede estar vacía")
    return (atencion or crear_atencion()).invoke({"consulta": consulta})
