from dotenv import load_dotenv
import logging
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
)

# Los avisos y errores quedan en errores.log (ignorado por git con *.log), no en la consola.
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="errores.log",
    filemode="a",
    encoding="utf-8",
    force=True,
)

logger = logging.getLogger(__name__)

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
    "montos ni tramos, y no pidas RUT ni datos personales. Responde en un "
    "solo párrafo:\n\n{mensaje}"
)

plantilla_queja = PromptTemplate.from_template(
    "Responde a esta queja de un ciudadano con empatía, reconociendo el "
    "problema antes de indicar dónde puede presentar su reclamo. No pidas "
    "RUT ni datos personales. Responde en un solo párrafo:\n\n{mensaje}"
)

plantilla_sugerencia = PromptTemplate.from_template(
    "Agradece esta sugerencia de un ciudadano y explica que será "
    "considerada para mejorar la orientación del asistente. Responde en un "
    "solo párrafo, sin firmas ni datos para completar:\n\n{mensaje}"
)


# Respaldo de la ruta de queja: no inventa normativa, solo confirma que el reclamo se recibió.
RESPUESTA_GENERICA = (
    "Lamentamos el inconveniente. Recibimos tu mensaje y nuestro equipo lo "
    "revisará. Mientras tanto, puedes presentar tu reclamo en fonasa.cl o en "
    "la oficina del Registro Social de Hogares de tu municipio."
)


def fallback_con_log(x):
    # exception_key="error" deja la excepción de la ruta en x["error"], para registrar la causa.
    logger.warning("La ruta de queja falló, se usa la respuesta de respaldo. Error: %s", x.get("error"))
    return RESPUESTA_GENERICA


respuesta_generica = RunnableLambda(fallback_con_log)


def construir_cadena_queja_segura(cadena_queja):
    return cadena_queja.with_fallbacks([respuesta_generica], exception_key="error")


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

RESPUESTA_ERROR = "No pudimos procesar tu mensaje en este momento. Intenta de nuevo más tarde."


def procesar_mensaje_seguro(cadena, mensaje):
    try:
        return cadena.invoke({"mensaje": mensaje})
    except Exception:
        # Red de seguridad: cubre fallos fuera de las rutas, como la clasificación.
        logger.exception("Error procesando mensaje")
        return RESPUESTA_ERROR


if __name__ == "__main__":
    load_dotenv()
    API_KEY = os.getenv("API_KEY")

    modelo = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", api_key=API_KEY) #modelo de lenguaje de Google Gemini)

    def mostrar_clasificacion(categoria):
        print(f"\nCLASIFICACIÓN: {categoria}")
        return categoria

    cadena_con_enrutamiento = construir_cadena_con_enrutamiento(
        construir_paso_clasificacion(modelo) | mostrar_clasificacion,
        cadena_queja=construir_cadena_queja_segura(plantilla_queja | modelo | StrOutputParser()),
        cadena_sugerencia=plantilla_sugerencia | modelo | StrOutputParser(),
        cadena_pregunta=plantilla_pregunta | modelo | StrOutputParser(),
    )

    print(procesar_mensaje_seguro(
        cadena_con_enrutamiento,
        "¿Qué necesito para actualizar mi Registro Social de Hogares",
    ))

    print(procesar_mensaje_seguro(
        cadena_con_enrutamiento,
        "Llevo semanas esperando que Fonasa actualice mi tramo y nadie me responde.",
    ))

    print(procesar_mensaje_seguro(
        cadena_con_enrutamiento,
        "Sería útil que el asistente me recordara los documentos antes de ir a la sucursal.",
    ))
