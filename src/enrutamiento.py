from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    RunnableBranch,
    RunnablePassthrough,
)

# --- Bloque 1: clasificación de la entrada ---
plantilla_clasificacion = PromptTemplate.from_template(
    "Clasifica el siguiente mensaje de un ciudadano sobre Fonasa o el "
    "Registro Social de Hogares en una sola palabra: pregunta, queja o "
    "sugerencia. Responde solo con esa palabra.\n\n{mensaje}"
)


def construir_paso_clasificacion(modelo):
    return (
        plantilla_clasificacion
        | modelo
        | StrOutputParser()
        | (lambda texto: texto.strip().lower())
    )


# --- Bloque 2: las tres rutas posibles, cada una con su propio prompt ---
plantilla_pregunta = PromptTemplate.from_template(
    "Responde esta pregunta de un ciudadano sobre Fonasa o el Registro "
    "Social de Hogares con lenguaje sencillo y precisión. No inventes "
    "montos ni tramos, y no pidas RUT ni datos personales:\n\n{mensaje}"
)

plantilla_queja = PromptTemplate.from_template(
    "Responde a esta queja de un ciudadano con empatía, reconociendo el "
    "problema antes de indicar dónde puede presentar su reclamo. No pidas "
    "RUT ni datos personales:\n\n{mensaje}"
)

plantilla_sugerencia = PromptTemplate.from_template(
    "Agradece esta sugerencia de un ciudadano y explica que será "
    "considerada para mejorar la orientación del asistente:\n\n{mensaje}"
)


# --- Bloque 3: la bifurcación que las conecta ---
def construir_cadena_con_enrutamiento(
    paso_clasificacion,
    cadena_queja=None,
    cadena_sugerencia=None,
    cadena_pregunta=None,
):
    # Sin ruta, se usa una que deja pasar la entrada: así cada prueba pasa solo la que verifica.
    cadena_queja = cadena_queja or RunnablePassthrough()
    cadena_sugerencia = cadena_sugerencia or RunnablePassthrough()
    cadena_pregunta = cadena_pregunta or RunnablePassthrough()

    bifurcacion = RunnableBranch(
        (lambda x: x["categoria"] == "queja", cadena_queja),
        (lambda x: x["categoria"] == "sugerencia", cadena_sugerencia),
        cadena_pregunta,
    )

    return (
        RunnablePassthrough.assign(categoria=paso_clasificacion)
        | bifurcacion
    )


if __name__ == "__main__":
    load_dotenv()
    API_KEY = os.getenv("API_KEY")

    modelo = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", api_key=API_KEY) #modelo de lenguaje de Google Gemini)

    def mostrar_clasificacion(categoria):
        print(f"\nCLASIFICACIÓN: {categoria}")
        return categoria

    cadena_con_enrutamiento = construir_cadena_con_enrutamiento(
        construir_paso_clasificacion(modelo) | mostrar_clasificacion,
        cadena_queja=plantilla_queja | modelo | StrOutputParser(),
        cadena_sugerencia=plantilla_sugerencia | modelo | StrOutputParser(),
        cadena_pregunta=plantilla_pregunta | modelo | StrOutputParser(),
    )

    print(cadena_con_enrutamiento.invoke(
        {"mensaje": "¿Qué necesito para actualizar mi Registro Social de Hogares?"}
    ))

    print(cadena_con_enrutamiento.invoke(
        {"mensaje": "Llevo semanas esperando que Fonasa actualice mi tramo y nadie me responde."}
    ))

    print(cadena_con_enrutamiento.invoke(
        {"mensaje": "Sería útil que el asistente me recordara los documentos antes de ir a la sucursal."}
    ))
