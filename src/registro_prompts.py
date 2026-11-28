"""Bloque 32, paso 1: dos versiones reales del prompt de sistema, con huella y diff."""
from datetime import date

from logging_rag import PROMPT_SISTEMA  #Versión actual (flujo RAG del Bloque 31)
from logs_rag import generar_huella
from versionado_prompt_langgraph import diff_prompts

NOMBRE = "prompt_sistema_rag"

#Versión anterior: el mensaje "system" de ejecutar_consulta() en logs_rag.py, copiado tal cual
PROMPT_ANTERIOR = (
    "Eres un asistente de soporte. Cita la fuente de cada afirmacion con su numero entre corchetes, "
    "como [1]. Si el contexto no alcanza para responder, dilo explicitamente en vez de inventar"
)


def registrar(versiones, nombre, texto, autor, nota, modelo):
    version = {"nombre": nombre, "huella": generar_huella(texto), "texto": texto, "autor": autor,
               "fecha": str(date.today()), "nota": nota, "modelo": modelo}
    versiones.append(version)
    return version


def ultima(versiones, nombre):
    candidatas = [v for v in versiones if v["nombre"] == nombre]
    return candidatas[-1] if candidatas else None


def versiones_del_proyecto():
    versiones = []
    registrar(versiones, NOMBRE, PROMPT_ANTERIOR, "Carlo Echeverría", "version original: asistente de soporte generico",
              "gemini-3.5-flash-lite")
    registrar(versiones, NOMBRE, PROMPT_SISTEMA, "Carlo Echeverría",
              "acota el rol a tramites sociales, exige usar solo el contexto y agrega instruccion anti-inyeccion",
              "gemini-3.5-flash-lite, temperature=0")
    return versiones


if __name__ == "__main__":
    versiones = versiones_del_proyecto()
    for v in versiones:
        print(v["huella"], "-", v["fecha"], "-", v["modelo"], "-", v["nota"])

    v1, v2 = versiones
    assert v1["huella"] != v2["huella"], "las dos versiones tienen la misma huella"
    assert ultima(versiones, NOMBRE) is v2, "ultima() no devuelve la version mas reciente"
    print("ultima version:", ultima(versiones, NOMBRE)["huella"])
    print("\n".join(diff_prompts(v1["texto"], v2["texto"])))
