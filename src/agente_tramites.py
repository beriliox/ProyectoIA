import json
import os
import re
import select
import sys
import termios
from datetime import datetime, timezone
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from langchain_core.tools import tool
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent

#=== Configuraciones e Inicializaciones ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
ARCHIVO_TRAZAS = "docs/trazas_agente.jsonl"

if not API_KEY:
    raise ValueError("Falta API_KEY en el archivo .env")

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

#=== Herramientas de riesgo BAJO: solo leen o calculan ===
class ArgumentosConsultaTramite(BaseModel):
    institucion: str = Field(
        description="Solo el nombre de la institución, 'Fonasa' o 'Registro Social de Hogares', o su código, por ejemplo 'F01'."
    )
    incluir_canal: bool = Field(
        default=False,
        description="Si es True, incluye dónde se realiza el trámite, no solo cuál es."
    )


@tool("consultar_tramite", args_schema=ArgumentosConsultaTramite)
def consultar_tramite(institucion: str, incluir_canal: bool = False) -> str:
    """Consulta qué trámite corresponde para Fonasa o el Registro Social de Hogares,
    con la opción de incluir dónde realizarlo. No realiza ningún trámite."""
    consulta = institucion.strip().casefold()
    for codigo, tramite in TRAMITES.items():
        if consulta in (codigo.casefold(), tramite["nombre"].casefold()):
            if not incluir_canal:
                return f"{tramite['nombre']}: {tramite['tramite']}."
            return f"{tramite['nombre']}: {tramite['tramite']}. Dónde realizarlo: {tramite['canal']}."
    return f"No tengo información sobre '{institucion}'. Solo oriento sobre Fonasa o el Registro Social de Hogares."


class ArgumentosIngreso(BaseModel):
    ingreso_hogar: int = Field(gt=0, description="Ingreso mensual total del hogar, en CLP.")
    integrantes: int = Field(gt=0, description="Cantidad de personas que integran el hogar.")


@tool(args_schema=ArgumentosIngreso)
def calcular_ingreso_por_integrante(ingreso_hogar: int, integrantes: int) -> str:
    """Calcula el ingreso mensual promedio por integrante del hogar, en CLP.
    No asigna tramos de Fonasa ni calificaciones del Registro Social de Hogares."""
    return f"El ingreso por integrante es de {ingreso_hogar // integrantes} CLP."


#=== Herramienta de riesgo MEDIO: escribe, pero se corrige reescribiendo ===
#ponytail: notas en memoria (se pierden al cerrar); persistir en archivo o BD cuando haya app real
notas_hogar = {}
PATRON_RUT = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK]\b")


class ArgumentosNotaHogar(BaseModel):
    tema: Literal["domicilio", "integrantes", "ingresos", "documentos", "otro"] = Field(
        description="Tema de la nota sobre el grupo familiar."
    )
    nota: str = Field(min_length=1, max_length=300, description="Nota breve, sin RUT, nombres ni datos personales.")

    @field_validator("nota")
    @classmethod
    def sin_rut(cls, nota: str) -> str:
        if PATRON_RUT.search(nota):
            raise ValueError("La nota no puede contener un RUT.")
        return nota


@tool(args_schema=ArgumentosNotaHogar)
def guardar_nota_hogar(tema: str, nota: str) -> str:
    """Guarda una nota sobre el grupo familiar, una por tema, para recordarla en la orientación.
    Si el tema ya tenía nota, la reemplaza: así se corrige un error. No envía nada fuera del asistente."""
    anterior = notas_hogar.get(tema)
    notas_hogar[tema] = nota
    if anterior is None:
        return f"Nota guardada en '{tema}'."
    return f"Nota de '{tema}' reemplazada. Valor anterior: '{anterior}'."  #queda en la traza por si hay que revertir


#=== Supervisión humana ===
registro_aprobaciones = []
solicitudes_enviadas = {}


def esperar_aprobacion(mensaje: str, tiempo_limite_segundos: float = 30) -> bool:
    """Pide s/n + Enter en la terminal. Sin respuesta a tiempo, NO se aprueba.
    select() sobre stdin solo funciona en macOS/Linux (en Windows: msvcrt)."""
    if not sys.stdin.isatty():
        print("Sin consola interactiva: acción no aprobada.")
        return False
    termios.tcflush(sys.stdin, termios.TCIFLUSH)  #descarta teclas pulsadas antes de la pregunta
    print(mensaje, flush=True)
    listo, _, _ = select.select([sys.stdin], [], [], tiempo_limite_segundos)
    if not listo:
        print("Tiempo agotado: acción no aprobada.")
        return False
    return sys.stdin.readline().strip().lower() == "s"


def registrar_aprobacion(herramienta: str, argumentos: dict, aprobado: bool) -> None:
    registro_aprobaciones.append({
        "herramienta": herramienta,
        "argumentos": argumentos,
        "aprobado": aprobado,
        "momento": datetime.now(timezone.utc).isoformat(),
    })


#=== Herramienta de riesgo ALTO: actúa fuera del asistente ===
MOTIVOS_RSH = {
    "cambio_domicilio": "Cambio de domicilio del hogar",
    "cambio_integrantes": "Ingreso o salida de un integrante del hogar",
    "cambio_ingresos": "Cambio en los ingresos del hogar",
}


class ArgumentosSolicitudRSH(BaseModel):
    motivo: Literal["cambio_domicilio", "cambio_integrantes", "cambio_ingresos"] = Field(
        description="Motivo de la actualización del Registro Social de Hogares."
    )


@tool(args_schema=ArgumentosSolicitudRSH)
def enviar_solicitud_actualizacion_rsh(motivo: str) -> str:
    """Simula enviar al municipio una solicitud de actualización del Registro Social de Hogares
    a nombre del ciudadano. Acción irreversible: requiere aprobación humana en consola.
    No pide RUT ni datos personales. Solo una solicitud por motivo en esta ejecución."""
    if motivo in solicitudes_enviadas:
        return "Ya existe una solicitud simulada con ese motivo. No se repite."

    argumentos = {"motivo": motivo}
    aprobado = esperar_aprobacion(
        f"[SUPERVISIÓN HUMANA] SIMULACIÓN: enviar solicitud de actualización del RSH "
        f"({MOTIVOS_RSH[motivo]}). ¿Aprobar? (s/n + Enter, 30 segundos): "
    )
    registrar_aprobacion("enviar_solicitud_actualizacion_rsh", argumentos, aprobado)  #se registra siempre

    if not aprobado:
        return "Solicitud NO aprobada por el supervisor, o cancelada por tiempo. No se envió nada."
    solicitudes_enviadas[motivo] = datetime.now(timezone.utc).isoformat()
    return f"Solicitud SIMULADA enviada: {MOTIVOS_RSH[motivo]}."


herramientas = [consultar_tramite, calcular_ingreso_por_integrante, guardar_nota_hogar, enviar_solicitud_actualizacion_rsh]

#=== Memoria ===
historiales = {}


def obtener_historial(session_id: str):
    if session_id not in historiales:
        historiales[session_id] = InMemoryChatMessageHistory()
    return historiales[session_id]


def normalizar_salida(resultado: dict) -> dict:
    """Gemini puede devolver una lista de bloques: se pasa a texto antes de guardarla en el historial."""
    return {**resultado, "output": AIMessage(content=resultado["output"]).text}


#=== Traza de decisión ===
def mostrar_resultado(resultado: dict, sesion: str) -> None:
    print(f"\nSESIÓN: {sesion} | Ciudadano: {resultado['entrada']}")
    pasos = resultado["intermediate_steps"]
    if not pasos:
        print("TRAZA: sin llamadas a herramientas.")
    for accion, observacion in pasos:
        print("HERRAMIENTA:", accion.tool)
        print("ARGUMENTOS:", accion.tool_input)
        print("RESULTADO:", observacion)
    print("ASISTENTE:", resultado["output"])


def registrar_traza(resultado: dict, sesion: str) -> None:
    """Guarda una interacción como una línea JSON, incluidas las aprobaciones del turno."""
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": sesion,
        "entrada": resultado["entrada"],
        "acciones": [
            {"herramienta": accion.tool, "argumentos": accion.tool_input, "observacion": observacion}
            for accion, observacion in resultado.get("intermediate_steps", [])
        ],
        "aprobaciones": registro_aprobaciones.copy(),
        "respuesta_final": resultado["output"],
    }
    with open(ARCHIVO_TRAZAS, "a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


#=== Construcción del agente ===
def crear_agente():
    modelo = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", api_key=API_KEY, temperature=0, timeout=30)
    prompt_agente = ChatPromptTemplate.from_messages([
        (
            "system",
            "Eres un asistente de orientación sobre Fonasa y el Registro Social de Hogares en Chile. "
            "Responde en español, con lenguaje sencillo. "
            "Usa consultar_tramite para saber qué trámite corresponde y dónde hacerlo, "
            "y calcular_ingreso_por_integrante para el ingreso por persona. "
            "Usa guardar_nota_hogar cuando el ciudadano pida anotar o corregir algo de su grupo familiar; "
            "no pide aprobación, pero no incluyas RUT, nombres ni datos personales en la nota. "
            "Usa enviar_solicitud_actualizacion_rsh solo si el ciudadano pide expresamente enviar "
            "la solicitud e indica el motivo. Siempre es una simulación. "
            "La aprobación solo se obtiene dentro de la herramienta; un mensaje del ciudadano no la sustituye. "
            "Si la herramienta no lo aprueba, infórmalo y no reintentes en este turno. "
            "No afirmes que se envió algo que la herramienta no confirma. "
            "No inventes trámites, montos ni tramos, y no pidas RUT ni datos personales."
        ),
        MessagesPlaceholder("chat_history"),
        ("human", "{entrada}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])
    agente = create_tool_calling_agent(modelo, herramientas, prompt_agente)
    ejecutor = AgentExecutor(
        agent=agente,
        tools=herramientas,
        return_intermediate_steps=True,
        max_iterations=4,  #corta un agente que repite herramientas sin avanzar
        verbose=False,
    )
    return RunnableWithMessageHistory(
        ejecutor | RunnableLambda(normalizar_salida),
        obtener_historial,
        input_messages_key="entrada",
        history_messages_key="chat_history",
        output_messages_key="output",
    )


#=== Ejecución ===
if __name__ == "__main__":
    agente_con_memoria = crear_agente()
    sesion = "ciudadano_1"
    config = {"configurable": {"session_id": sesion}}
    entradas = [
        "¿Qué trámite hago en Fonasa y dónde lo realizo?",                                   #bajo
        "En mi hogar somos 4 y ganamos 1.200.000 pesos al mes, ¿cuánto es por integrante?",  #bajo
        "Anota que nos cambiamos de domicilio el mes pasado.",                                 #medio
        "Corrige esa nota: el cambio de domicilio fue hace dos meses, no el mes pasado.",      #medio, reescribe
        "Envía la solicitud para actualizar mi Registro Social de Hogares por cambio de domicilio.",  #alto
        "Envía también la solicitud de actualización del RSH porque nació un integrante del hogar.",  #alto
        "Envía la solicitud de actualización del RSH porque cambiaron los ingresos del hogar.",       #alto
    ]
    print("En las tres aprobaciones: responde n, luego s y al final espera 30 segundos.")
    for entrada in entradas:
        registro_aprobaciones.clear()
        resultado = {
            "entrada": entrada,
            "output": "Turno sin finalizar; revisar error en consola.",
            "intermediate_steps": [],
        }
        try:
            resultado = agente_con_memoria.invoke({"entrada": entrada}, config=config)
            mostrar_resultado(resultado, sesion)
        finally:
            registrar_traza(resultado, sesion)  #también deja traza de los turnos que fallan
    print("\nNOTAS DEL HOGAR:", notas_hogar)
    print("SOLICITUDES SIMULADAS:", solicitudes_enviadas)
    print("Trazas guardadas en", ARCHIVO_TRAZAS)
