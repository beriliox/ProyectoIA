"""Capa de peticiones: clasifica la consulta y la deriva a una sola ruta (patrón del bloque 19).

    consulta ─► clasificar ─► normativa       → orientar()  (llm.py, REST con reintentos y costo)
                          ├► reporte         → aviso fijo  (pendiente: tablas tramite/paso_tramite)
                          └► conversacional  → respuesta breve del modelo (ruta por defecto)

Es lo que FastAPI expondrá en el M3: un POST que llama a atender().
"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough

from app.prompts import CLASIFICADOR, CONVERSACION


def normalizar_intencion(texto: str) -> str:
    return texto.strip().lower().rstrip(".").strip()


def construir_clasificador(modelo):
    return PromptTemplate.from_template(CLASIFICADOR) | modelo | StrOutputParser() | normalizar_intencion


def construir_ruta_conversacional(modelo):
    return PromptTemplate.from_template(CONVERSACION) | modelo | StrOutputParser()


def responder_reporte(_datos: dict) -> str:
    return "Los reportes de trámites todavía no están disponibles en esta versión."


def construir_atencion(clasificador, ruta_normativa, ruta_reporte, ruta_conversacional):
    """Cada ruta recibe {"consulta", "intencion"} y devuelve la respuesta."""
    bifurcacion = RunnableBranch(
        (lambda d: d["intencion"] == "normativa", ruta_normativa),
        (lambda d: d["intencion"] == "reporte", ruta_reporte),
        ruta_conversacional,  # por defecto: una clasificación rara nunca termina inventando normativa
    )
    return RunnablePassthrough.assign(intencion=clasificador) | RunnablePassthrough.assign(respuesta=bifurcacion)


def crear_atencion():
    from app.llm import crear_modelo_langchain
    from app.orientador import orientar

    modelo = crear_modelo_langchain()
    return construir_atencion(
        construir_clasificador(modelo),
        RunnableLambda(lambda d: orientar(d["consulta"])),
        RunnableLambda(responder_reporte),
        construir_ruta_conversacional(modelo),
    )


def atender(consulta: str, atencion=None) -> dict:
    if not consulta or not consulta.strip():
        raise ValueError("La consulta no puede estar vacía")
    return (atencion or crear_atencion()).invoke({"consulta": consulta})
