import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()
API_KEY = os.getenv("API_KEY")
modelo = ChatGoogleGenerativeAI(model="gemini-3.8-flash", api_key=API_KEY)

plantilla = PromptTemplate.from_template(
    "Explica {tema} en dos oraciones para alguien que está comenzando."
)

paso = plantilla | modelo | StrOutputParser()

resultado = paso.invoke({"tema": "tokenización"})

print(resultado)
print(type(resultado))