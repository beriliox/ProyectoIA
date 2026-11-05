from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    RunnableBranch,
    RunnablePassthrough,
)

load_dotenv()
API_KEY = os.getenv("API_KEY")
modelo = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", api_key=API_KEY) #modelo de lenguaje de Google Gemini)

plantilla_clasificacion = PromptTemplate.from_template(
    "Clasifica el siguiente mensaje de soporte en una sola "
    "palabra: pregunta, queja o sugerencia. Responde solo "
    "con esa palabra.\n\n{mensaje}"
)

paso_clasificacion = (
    plantilla_clasificacion
    | modelo
    | StrOutputParser()
    | (lambda texto: texto.strip().lower())
)

cadena_pregunta = (
    PromptTemplate.from_template(
        "Responde esta pregunta técnica con precisión:\n\n{mensaje}"
    )
    | modelo
    | StrOutputParser()
)

cadena_queja = (
    PromptTemplate.from_template(
        "Responde a esta queja con empatía, reconociendo el "
        "problema antes de ofrecer una solución:\n\n{mensaje}"
    )
    | modelo
    | StrOutputParser()
)

cadena_sugerencia = (
    PromptTemplate.from_template(
        "Agradece esta sugerencia y explica cómo se evaluará "
        "dentro del producto:\n\n{mensaje}"
    )
    | modelo
    | StrOutputParser()
)

bifurcacion = RunnableBranch(
    (lambda x: x["categoria"] == "queja", cadena_queja),
    (lambda x: x["categoria"] == "sugerencia", cadena_sugerencia),
    cadena_pregunta,
)

cadena_con_enrutamiento = (
    RunnablePassthrough.assign(categoria=paso_clasificacion)
    | bifurcacion
)

resultado = cadena_con_enrutamiento.invoke(
    {"mensaje": "La app se cierra cada vez que subo una foto."}
)
print(resultado)