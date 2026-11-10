#Herramientas Personalizadas
#Intro a Memoria
import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import (
    AgentExecutor,
    create_tool_calling_agent,
)
from pydantic import BaseModel, Field
from langchain_core.chat_history import InMemoryChatMessageHistory #Crear el historial en base a la sesión
from langchain_core.runnables.history import RunnableWithMessageHistory #Encapsular mi agente para que implemente la memoria

#=== Configuraciones e Inicializaciones===
load_dotenv()
API_KEY = os.getenv("API_KEY")
modelo = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", api_key=API_KEY)

#=== Esquemas de Validación ===
class ArgumentosConsultaTramite(BaseModel):
    """
    Esquema para documentar y validar argumentos campo por campo ante el LLM.
    """
    institucion: str = Field(
        description="Solo el nombre de la institución, 'Fonasa' o 'Registro Social de Hogares', o su código, por ejemplo 'F01'. No la frase completa del usuario."
    )
    incluir_canal: bool = Field(
        default=False,
        description="Si es True, incluye dónde se realiza el trámite, no solo cuál es."
    )

#=== Base de Datos ===
TRAMITES = {
    "F01": {
        "nombre": "Fonasa",
        "tramite": "Actualizar el tramo de Fonasa",
        "canal": "Sucursal virtual en fonasa.cl o una sucursal presencial de Fonasa",
    },
    "R01": {
        "nombre": "Registro Social de Hogares",
        "tramite": "Actualizar los datos del Registro Social de Hogares",
        "canal": "registrosocial.gob.cl o la oficina del Registro Social de Hogares de tu municipio",
    },
}

#=== Herramientas ===
@tool("consultar_tramite", args_schema=ArgumentosConsultaTramite) #LangChain transforma esta clase en un esquema JSON que se envía al LLM
def consultar_tramite(institucion: str, incluir_canal: bool = False) -> str:
    """
    Consulta qué trámite corresponde para Fonasa o el Registro Social de Hogares, con la opción de incluir dónde realizarlo.
    Usar cuando el usuario pregunta qué trámite hacer o dónde hacerlo.
    """
    consulta = institucion.strip().casefold()

    for codigo, tramite in TRAMITES.items():
        if consulta in (codigo.casefold(), tramite["nombre"].casefold()):
            #Si no se solicita el canal, retornamos solo el trámite
            if not incluir_canal:
                return f"{tramite['nombre']}: {tramite['tramite']}."
            #Si sí se solicita, se agrega dónde realizarlo
            return f"{tramite['nombre']}: {tramite['tramite']}. Dónde realizarlo: {tramite['canal']}."

    return f"No tengo información sobre '{institucion}'. Solo oriento sobre Fonasa o el Registro Social de Hogares."

@tool
def calcular_ingreso_por_integrante(ingreso_hogar: int, integrantes: int) -> str:
    """Calcula el ingreso mensual promedio por integrante del hogar, en CLP.
    Usar cuando el usuario entrega el ingreso total del hogar y cuántas personas lo integran.
    No asigna tramos de Fonasa ni calificaciones del Registro Social de Hogares."""
    if ingreso_hogar <= 0 or integrantes <= 0:
        return "Error: el ingreso y el número de integrantes deben ser mayores que cero."
    return f"El ingreso por integrante es de {ingreso_hogar // integrantes} CLP."

#Listado de herramientas
herramientas = [consultar_tramite, calcular_ingreso_por_integrante]

#=== Gestión de historial en memoria ===
historiales = {}
"""
historiales = {
    'ciudadano_1': {MENSAJES},
    'ciudadano_2': {MENSAJES},
}
"""
def obtener_historial(session_id: str):
    if session_id not in historiales:
        historiales[session_id] = InMemoryChatMessageHistory()
    return historiales[session_id]


#=== Construcción del agente ===
prompt_agente = ChatPromptTemplate.from_messages([
    (
        "system", "Eres un asistente de orientación sobre Fonasa y el Registro Social de Hogares en Chile. "
        "Responde en español, con lenguaje sencillo, usando las herramientas disponibles cuando las necesites. "
        "No inventes trámites, montos ni tramos, y no pidas RUT ni datos personales."
    ),
    MessagesPlaceholder("chat_history"), #Lo que se dijo en turnos anteriores (va ANTES del mensaje humano)
    ("human", "{entrada}"),
    MessagesPlaceholder("agent_scratchpad") #El razonamiento de ESTE turno (va DESPUÉS)
])

agente = create_tool_calling_agent(modelo, herramientas, prompt_agente)

ejecutor_agente = AgentExecutor(
    agent=agente,
    tools=herramientas,
    verbose=True,
    return_intermediate_steps=True,
)

limpiar_salida = RunnableLambda(
    lambda d: {**d, "output": d["output"][0]["text"] if isinstance(d.get("output"), list) else d.get("output")}
)

cadena_agente = ejecutor_agente | limpiar_salida

#agente con memoria
agente_con_memoria = RunnableWithMessageHistory(
    #El historial guarda "output" como mensaje: sin pasarlo a texto, la lista de bloques falla en el turno 2.
    cadena_agente,
    obtener_historial,
    input_messages_key="entrada",         #Coincide con {entrada} del prompt
    history_messages_key="chat_history",  #Coincide con MessagesPlaceholder("chat_history")
    output_messages_key="output",
)

#=== Ejecución ===
if __name__ == "__main__":
    #Prueba 1: dos turnos en la misma sesión
    config = {"configurable": {"session_id": "ciudadano_456"}}

    resultado = agente_con_memoria.invoke(
        {"entrada": "¿Qué trámite hago en Fonasa y dónde lo realizo?"}, config
    )
    print("Respuesta: ", resultado["output"])

    resultado = agente_con_memoria.invoke(
        {"entrada": "¿Y el equivalente en el Registro Social de Hogares?"}, config
    )
    print("Respuesta: ", resultado["output"])

    #Prueba 2: dos sesiones no se mezclan
    config_ciudadano_1 = {"configurable": {"session_id": "ciudadano_1"}}
    config_ciudadano_2 = {"configurable": {"session_id": "ciudadano_2"}}

    agente_con_memoria.invoke({"entrada": "Estoy preguntando por Fonasa."}, config_ciudadano_1)
    resultado = agente_con_memoria.invoke({"entrada": "¿Sobre qué institución te pregunté?"}, config_ciudadano_2)
    print("Respuesta: ", resultado["output"])

    print(obtener_historial("ciudadano_1"))
    print(obtener_historial("ciudadano_2"))

    print("Mensajes ciudadano_1:", len(obtener_historial("ciudadano_1").messages))
    print("Mensajes ciudadano_2:", len(obtener_historial("ciudadano_2").messages))