import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor

load_dotenv()
API_KEY = os.getenv("API_KEY")

# Textos referenciales: valídalos con la fuente oficial (fonasa.cl, registrosocial.gob.cl) antes de usarlos.
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

@tool
def consultar_tramite(consulta: str) -> str:
    """Consulta qué trámite corresponde y dónde se realiza, para Fonasa o el Registro Social de Hogares.
    Recibe solo el nombre de la institución, exactamente Fonasa o Registro Social de Hogares,
    o su código, como F01; no la frase completa del usuario.
    Úsala cuando el usuario pregunte qué trámite hacer o dónde hacerlo.
    No calcula ingresos ni realiza trámites.
    """
    consulta_limpia = consulta.strip().casefold()

    for codigo, tramite in TRAMITES.items():
        coincide_codigo = consulta_limpia == codigo.casefold()
        coincide_nombre = consulta_limpia == tramite["nombre"].casefold()

        if coincide_codigo or coincide_nombre:
            return (
                f"Institución: {tramite['nombre']}. "
                f"Trámite: {tramite['tramite']}. "
                f"Dónde realizarlo: {tramite['canal']}."
            )

    return "Trámite no encontrado. Pide al usuario que indique si su consulta es sobre Fonasa o el Registro Social de Hogares."

@tool
def calcular_ingreso_por_integrante(ingreso_hogar: int, integrantes: int) -> str:
    """Calcula el ingreso mensual promedio por integrante del hogar, en CLP.
    Úsala cuando el usuario entregue el ingreso total del hogar y cuántas personas lo integran.
    No asigna tramos de Fonasa ni calificaciones del Registro Social de Hogares.
    """
    if ingreso_hogar <= 0 or integrantes <= 0:
        return "Error: el ingreso y el número de integrantes deben ser mayores que cero."

    ingreso_por_integrante = ingreso_hogar // integrantes

    return (
        f"Ingreso del hogar: {ingreso_hogar} CLP. "
        f"Integrantes: {integrantes}. "
        f"Ingreso por integrante: {ingreso_por_integrante} CLP."
    )

modelo = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    api_key=API_KEY,
    temperature=0,
    timeout=20,
    max_retries=0,
)

herramientas = [consultar_tramite, calcular_ingreso_por_integrante]

instrucciones = (
    "Eres un asistente de orientación sobre Fonasa y el Registro Social de Hogares en Chile. "
    "Responde en español, con lenguaje sencillo. "
    "Para saber qué trámite corresponde y dónde hacerlo, usa consultar_tramite "
    "con solo el nombre de la institución: Fonasa o Registro Social de Hogares. "
    "Para calcular el ingreso por integrante del hogar, usa calcular_ingreso_por_integrante. "
    "No inventes trámites, montos, tramos ni requisitos. "
    "Si falta información, pídela. "
    "Si la institución no es Fonasa ni el Registro Social de Hogares, informa que no tienes información sobre ella. "
    "No pidas RUT ni datos personales. "
    "Para un saludo, responde directamente sin usar herramientas. "
    "Solo orientas; no realizas trámites."
)

prompt = ChatPromptTemplate.from_messages([
    ("system", instrucciones),
    ("human", "{entrada}"),
    MessagesPlaceholder("agent_scratchpad"),
])

agente = create_tool_calling_agent(
    llm=modelo,
    tools=herramientas,
    prompt=prompt,
)

ejecutor = AgentExecutor(
    agent=agente,
    tools=herramientas,
    return_intermediate_steps=True,
    verbose=True,
    max_iterations=4,
)

def probar(entrada: str):
    print("\nPREGUNTA:", entrada)

    resultado = ejecutor.invoke({"entrada": entrada})
    pasos = resultado["intermediate_steps"]

    print("\nTRAZA DE HERRAMIENTAS:")

    if not pasos:
        print("No se utilizaron herramientas.")

    for numero, (accion, observacion) in enumerate(pasos, start=1):
        print(f"\nPaso {numero}")
        print("Herramienta:", accion.tool)
        print("Argumentos:", accion.tool_input)
        print("Observación:", observacion)

    print("\nRESPUESTA FINAL:")

    salida = resultado["output"]

    if isinstance(salida, str):
        print(salida)
    else:
        texto = "\n".join(
            bloque["text"]
            for bloque in salida
            if isinstance(bloque, dict)
            and bloque.get("type") == "text"
            and isinstance(bloque.get("text"), str)
        )
        print(texto)

if __name__ == "__main__":
    print("Asistente social")

    nombres = ", ".join(
        tramite["nombre"]
        for tramite in TRAMITES.values()
    )

    print("Instituciones disponibles:", nombres)
    print("Escribe 'salir' para terminar.")

    while True:
        entrada = input("\nTu pregunta: ").strip()

        if entrada.lower() == "salir":
            break

        if not entrada:
            continue

        probar(entrada)
