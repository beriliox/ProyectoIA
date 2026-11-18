from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI #Modelo para instanciar gemini

from rag_indexer import formatear_contexto #Contexto numerado [1], [2] y diccionario de citas
from rag_indexer_asistente_social import cargar_vectorstore

load_dotenv()

#Plantilla que obliga a usar SOLO el contexto recuperado y a citar [1], [2]
PROMPT_TEMPLATE = """Responde la pregunta usando SOLO el contexto de abajo. Cita la \
fuente de cada afirmacion con su numero entre corchetes, como [1]. Si el contexto no \
alcanza para responder, dilo explicitamente en vez de inventar.

Contexto:
{contexto}

Pregunta: {pregunta}

Respuesta:"""

"""
Recupera los k chunks más relevantes y arma el prompt con el contexto numerado.
Se conecta con Chroma(...) y NO con from_documents, para no reindexar en cada pregunta
"""
def construir_prompt(pregunta, persist_directory, collection_name, k=3):
    vs = cargar_vectorstore(persist_directory, collection_name)
    retriever = vs.as_retriever(search_kwargs={"k": k})

    chunks_recuperados = retriever.invoke(pregunta) #SI GASTA TOKENS (embedding de la pregunta)
    contexto, citas = formatear_contexto(chunks_recuperados)
    prompt = PROMPT_TEMPLATE.format(contexto=contexto, pregunta=pregunta)
    return prompt, citas

if __name__ == "__main__":
    CARPETA_DB = "vectorstore"
    COLECCION = "asistente_social"
    K = 3

    modelo = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)

    preguntas = [
        "¿Dónde actualizo mi tramo de Fonasa?",
        "¿Qué pasa si el servicio se demora en contestar?",
        "¿Cuál es el monto del bono de invierno?", #El corpus no lo responde: el modelo debe decir que no sabe
    ]

    for pregunta in preguntas:
        prompt, citas = construir_prompt(pregunta, CARPETA_DB, COLECCION, K)
        respuesta = modelo.invoke(prompt) #SI GASTA TOKENS

        print("--PROMPT--")
        print(prompt)
        print("--CITAS--")
        print(citas)
        print("--RESPUESTA--")
        print(respuesta.text)
        print()
