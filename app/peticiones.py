"""Capa 3, peticiones: clasifica la consulta y la deriva a una sola ruta (bloque 19).

    consulta ─► clasificar ─┬► normativa       → cadena de tres pasos
                            └► conversacional  → respuesta breve (ruta por defecto)

Cada ruta tiene su fallback y atender() tiene un try/except general (bloque 20).

Base en los ejemplos: ejemplos/bifurcacion.py, ejemplos/enrutamiento.py y ejemplos/enrutamiento_callback.py.
Es lo que FastAPI expondrá en el Módulo 3.
"""
import logging

from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough

from app.cadenas import construir_cadena_conversacional, construir_cadena_normativa, construir_clasificador

logger = logging.getLogger(__name__)

# Los respaldos nunca redactan normativa con otro modelo: eso sería inventar beneficios (bloque 17).
RESPALDO_NORMATIVA = (
    "En este momento no pude consultar la información de Fonasa o del Registro Social de Hogares. "
    "Intenta de nuevo en unos minutos."
)
RESPALDO_CONVERSACIONAL = (
    "Hola, puedo orientarte sobre Fonasa y el Registro Social de Hogares. ¿En qué te ayudo?"
)
RESPUESTA_ERROR = "No pudimos procesar tu consulta en este momento. Intenta de nuevo más tarde."


def con_respaldo(ruta, texto: str):
    def responder_respaldo(_datos):
        logger.warning("Falló una ruta; se usa la respuesta de respaldo")
        return texto

    return ruta.with_fallbacks([RunnableLambda(responder_respaldo)])


def construir_atencion(clasificador, ruta_normativa, ruta_conversacional):
    """Cada ruta recibe {"consulta", "intencion"} y devuelve el texto de la respuesta."""
    bifurcacion = RunnableBranch(
        (lambda datos: datos["intencion"] == "normativa", con_respaldo(ruta_normativa, RESPALDO_NORMATIVA)),
        con_respaldo(ruta_conversacional, RESPALDO_CONVERSACIONAL),  # por defecto: una clasificación rara nunca termina inventando normativa
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
    try:
        return (atencion or crear_atencion()).invoke({"consulta": consulta})
    except Exception:
        # red de seguridad: cubre lo que ningún fallback de ruta alcanza, como la clasificación
        logger.exception("Error procesando la consulta")
        return {"consulta": consulta, "intencion": "error", "respuesta": RESPUESTA_ERROR}
