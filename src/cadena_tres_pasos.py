import os

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

def construir_cadena(modelo):
    plantilla_extraer = PromptTemplate.from_template(
        "Resume en dos líneas la situación de esta persona y qué necesita saber. "
        "No agregues información que no esté en la consulta:\n\n{consulta}"
    )

    plantilla_redactar = PromptTemplate.from_template(
        "Eres un orientador de trámites de Fonasa y del Registro Social de Hogares en Chile. "
        "A partir de esta situación, explica en un máximo de cuatro oraciones, con lenguaje "
        "sencillo, qué puede hacer la persona y dónde. No pidas RUT ni datos personales:\n\n{situacion}"
    )

    plantilla_revisar = PromptTemplate.from_template(
        "Revisa esta orientación para un ciudadano. Corrige el tono si es frío o técnico, "
        "sin agregar información nueva. Agrega [VERIFICAR] justo después de cada monto, "
        "porcentaje o tramo que mencione. Entrega solo el texto final:\n\n{borrador}"
    )

    extraer = plantilla_extraer | modelo | StrOutputParser()
    redactar = plantilla_redactar | modelo | StrOutputParser()
    revisar = plantilla_revisar | modelo | StrOutputParser()

    return (
        extraer
        | (lambda resultado: {"situacion": resultado})
        | redactar
        | (lambda resultado: {"borrador": resultado})
        | revisar
    )

if __name__ == "__main__":
    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    modelo = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", api_key=API_KEY)
    cadena = construir_cadena(modelo)

    consultas = [
      (
        "Me quedé sin trabajo el mes pasado y ahora no tengo ingresos. "
        "Estoy en el tramo C de Fonasa. ¿Puedo cambiarme de tramo para no pagar en el consultorio?"
      ),
      (
        "Tengo 4 cargas familiares y estoy en el tramo D de Fonasa. "
        "¿Puedo cambiarme al tramo C para pagar menos?"
      ),
      (
        "Quiero postular a un subsidio habitacional, pero no sé cómo funciona el Registro Social de Hogares. "
        "¿Qué información necesito y cómo puedo inscribirme?"
      ),
      (
        "Mi familia tiene ingresos bajos y queremos acceder a programas sociales. "
        "¿Cómo nos ayuda el Registro Social de Hogares y qué documentos necesitamos?"
      ),

    ]
    for consulta in consultas:
      print("\n" + "=" * 70)
      print("Consulta:", consulta)
      print("\n" + "-" * 70)
      print(cadena.invoke({"consulta": consulta}))
      print("\n" + "=" * 70 + "\n")