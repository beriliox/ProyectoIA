from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

API_KEY = os.getenv("API_KEY")

modelo = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", api_key=API_KEY)

plantilla_extraccion = PromptTemplate.from_template("Lee el siguiente texto y devuelve solos sus 3 puntos claves, uno por línea, sin desarrollarlos: \n\n {texto}")

#Pasos
#1. extraccion
paso_extraccion = plantilla_extraccion | modelo | StrOutputParser()

texto_prueba = [
  "Los modelos de lenguaje grandes generan texto "
  "prediciendo un token a la vez, basándose en el "
  "texto que ya generaron antes. Cada token puede "
  "ser una palabra completa, parte de una palabra, "
  "o un signo de puntuación. Antes de que el modelo "
  "genere una respuesta, el texto de entrada se "
  "divide en tokens, un proceso llamado tokenización."
]

# puntos = paso_extraccion.invoke({"texto": texto_prueba})
# print(puntos)

#2. simplificar o sobreescribir esos puntos. los puntos generados deben pasar a la siguiente
plantilla_simplificacion = PromptTemplate.from_template("Reescribe estos puntos enm lenguaje simple, sin jerga tecnica para alguien sin conocimientos tecnicos: \n\n {puntos}")

paso_simplificacion = plantilla_simplificacion | modelo | StrOutputParser()

# simple = paso_simplificacion.invoke({"puntos": puntos})

# print(simple)

#3. dar el formato correcto
plantilla_formato = PromptTemplate.from_template("Convierte este texto en una lista de viñetas markdown de máximo 3 líneas, sin introducción: \n\n {simple}")

paso_formato = plantilla_formato | modelo | StrOutputParser()
# formato = paso_formato.invoke({"simple": simple})
# print(formato)

#Sintaxis lambda -> lambda argumentos: expresion
cadena_tres_pasos = (
    plantilla_extraccion
    | modelo
    | StrOutputParser()
    | (lambda puntos: {"puntos": puntos})
    | plantilla_simplificacion
    | modelo
    | StrOutputParser()
    | (lambda simple: {"simple": simple})
    | plantilla_formato
    | modelo
    | StrOutputParser()
)

resultado = cadena_tres_pasos.invoke({"texto": texto_prueba})
print(resultado)