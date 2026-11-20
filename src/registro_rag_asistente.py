import json #Registrar en jsonl la info
from datetime import datetime, timezone
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI #Modelo para instanciar gemini

from rag_indexer import formatear_contexto
from rag_indexer_asistente_social import cargar_vectorstore
from registro_rag import PROMPT_TEMPLATE, medir, calcular_costo #Reuso la plantilla, el cronómetro y el cálculo de costo

load_dotenv()

#Registrar consulta del asistente social
def registrar_consulta(vectorstore, pregunta: str, k: int = 3) -> dict:
    """
    Ejecutar de punta a punta el RAG del asistente (Recuperación + Prompt con contexto + Generación con Gemini),
    medir la latencia de cada etapa y extraer los tokens consumidos (reales) y su costo
    """
    tiempos = {} #Latencia de cada etapa

    chat_model = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0) #Mismo modelo que recuperacion.py

    #Etapa 1: Embed de la pregunta y búsqueda vectorial en Chroma
    with medir(tiempos, "embed_y_busqueda"):
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        chunks = retriever.invoke(pregunta)

    #Etapa 2: Armado del prompt con los chunks formateados - Acción Local
    with medir(tiempos, "armado_prompt"):
        contexto, citas = formatear_contexto(chunks)
        prompt = PROMPT_TEMPLATE.format(contexto=contexto, pregunta=pregunta)

    #Etapa 3: Generación de la respuesta con Gemini
    with medir(tiempos, "generacion"):
        respuesta = chat_model.invoke(prompt)

    #Tokens reales: input_tokens, output_tokens, total_tokens. None si la respuesta no trae uso
    tokens_reales = dict(respuesta.usage_metadata) if respuesta.usage_metadata else None

    costo_usd = None
    if tokens_reales:
        costo_usd = calcular_costo(
            tokens_entrada = tokens_reales.get("input_tokens", 0),
            tokens_salida = tokens_reales.get("output_tokens", 0) #output_tokens YA INCLUYE tokens de razonamiento
        )

    #Factor crecimiento: cuánto creció el texto de entrada vs la pregunta solita
    factor_crecimiento = round(len(prompt) / len(pregunta), 1)

    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pregunta": pregunta,
        "k": k,
        "respuesta_generada": respuesta.text,
        "citas_disponibles": citas,
        "tiempos_ms": {etapa: round(seg * 1000, 2) for etapa, seg in tiempos.items()},
        "tiempo_total_ms": round(sum(tiempos.values()) * 1000, 2),
        "factor_crecimiento": f"{factor_crecimiento}x",
        "tokens": tokens_reales,
        "costo_estimado_usd": costo_usd #None si no hubo tokens
    }

    return registro

if __name__ == "__main__":
    CARPETA_DB = "vectorstore"
    COLECCION = "asistente_social" #La misma colección con la que se indexó
    ARCHIVO_REGISTROS = "registros_latencia_costo.jsonl"

    vs = cargar_vectorstore(CARPETA_DB, COLECCION)

    #Preguntas del conjunto de evaluación del Bloque 27, con distinto largo
    consultas = [
        ("¿Dónde actualizo mi tramo de Fonasa?", 3),
        ("Somos cinco en la casa, ¿cómo se saca lo que gana cada uno?", 3),
        ("¿Qué pasa si el servicio se demora en contestar?", 3),
        ("¿Qué pasa si el servicio se demora en contestar?", 6), #Misma pregunta con k=6: input_tokens debe crecer
    ]

    #"a": el archivo crece una línea por corrida para poder comparar
    with open(ARCHIVO_REGISTROS, "a", encoding="utf-8") as f:
        for pregunta, k in consultas:
            registro = registrar_consulta(vs, pregunta, k)
            print(json.dumps(registro, indent=2, ensure_ascii=False))
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
