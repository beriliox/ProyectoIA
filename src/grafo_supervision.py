"""Bloque 32, paso 2: pausa de LangGraph antes de activar una versión nueva del prompt."""
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agente_tramites import esperar_aprobacion  #s/n por consola; sin respuesta NO se aprueba (Bloque 23)
from registro_prompts import NOMBRE, ultima, versiones_del_proyecto
from versionado_prompt_langgraph import nuevo_thread_id, resolver


class EstadoDespliegue(TypedDict):
    huella_nueva: str
    aprobado: bool


def proponer(estado: EstadoDespliegue):
    return {}


def supervisar(estado: EstadoDespliegue):
    decision = interrupt({
        "motivo": "aprobar nueva version de prompt en produccion",
        "huella_propuesta": estado["huella_nueva"],
    })
    return {"aprobado": decision}


def aplicar(estado: EstadoDespliegue):
    #ponytail: solo informa; no cambia el prompt que usa logging_rag.py (pendiente en la matriz, R3)
    if estado["aprobado"] is True:
        print("version", estado["huella_nueva"], "activada")
    else:
        print("version", estado["huella_nueva"], "rechazada, se mantiene la anterior")
    return {}


grafo = StateGraph(EstadoDespliegue)
grafo.add_node("proponer", proponer)
grafo.add_node("supervisar", supervisar)
grafo.add_node("aplicar", aplicar)
grafo.add_edge(START, "proponer")
grafo.add_edge("proponer", "supervisar")
grafo.add_edge("supervisar", "aplicar")
grafo.add_edge("aplicar", END)
app_despliegue = grafo.compile(checkpointer=InMemorySaver())


if __name__ == "__main__":
    huella = ultima(versiones_del_proyecto(), NOMBRE)["huella"]

    #Dos solicitudes con thread_id distinto: responde "s" en una y "n" en la otra para probar ambos caminos
    for numero in (1, 2):
        config = {"configurable": {"thread_id": nuevo_thread_id()}}
        resultado = app_despliegue.invoke({"huella_nueva": huella, "aprobado": False}, config=config)
        assert "__interrupt__" in resultado, "el grafo no se detuvo antes de aplicar"
        pendiente = app_despliegue.get_state(config).interrupts[0].value
        print(f"\nSolicitud {numero} pendiente:", pendiente)
        decision = esperar_aprobacion("¿Activar esta versión? (s/n + Enter, 30 segundos): ")
        print("estado final:", resolver(app_despliegue, config, decision))
