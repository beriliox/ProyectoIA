#Bloque 24: indexación del corpus y persistencia de embeddings
#Corpus: documentación del asistente de orientación sobre Fonasa y el Registro Social de Hogares.
#Uso: python src/indexar_corpus.py  (pide el modo: indexar o verificar)
import os

from dotenv import load_dotenv
from langchain_text_splitters import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

clave = os.getenv("API_KEY")
coleccion = "asistente_social"  #el mismo nombre al indexar y al recargar, si no count() da 0

if not clave:
    raise ValueError("Falta API_KEY en el archivo .env")

if __name__ == "__main__":
    #Solo describe lo que el asistente hace hoy (sale del código del repo). No contiene normativa:
    #tramos, porcentajes y requisitos legales se agregan desde fuentes oficiales, nunca de memoria.
    corpus = [
        {
            "texto": "Para Fonasa, el trámite que orienta el asistente es actualizar el tramo de Fonasa. "
                     "Se realiza en la sucursal virtual en fonasa.cl o en una sucursal presencial de Fonasa.",
            "fuente": "src/agente_tramites.py (TRAMITES, F01)",
        },
        {
            "texto": "Para el Registro Social de Hogares, el trámite que orienta el asistente es actualizar los "
                     "datos del Registro Social de Hogares. Se realiza en registrosocial.gob.cl o en la oficina "
                     "del Registro Social de Hogares del municipio.",
            "fuente": "src/agente_tramites.py (TRAMITES, R01)",
        },
        {
            "texto": "El asistente calcula el ingreso mensual promedio por integrante dividiendo el ingreso total "
                     "del hogar por la cantidad de integrantes. Ambos valores deben ser mayores que cero. "
                     "Ese cálculo no asigna tramos de Fonasa ni calificaciones del Registro Social de Hogares.",
            "fuente": "src/agente_tramites.py (calcular_ingreso_por_integrante)",
        },
        {
            "texto": "El asistente puede guardar una nota breve sobre el grupo familiar, una por tema: domicilio, "
                     "integrantes, ingresos, documentos u otro. Es una acción de riesgo medio: no pide aprobación "
                     "y se corrige guardando otra nota del mismo tema, que reemplaza a la anterior. "
                     "La nota no puede contener RUT ni datos personales.",
            "fuente": "src/agente_tramites.py (guardar_nota_hogar)",
        },
        {
            "texto": "Enviar una solicitud de actualización del Registro Social de Hogares es una acción de riesgo "
                     "alto y en esta práctica es solo una simulación. Los motivos admitidos son cambio de domicilio, "
                     "ingreso o salida de un integrante del hogar y cambio en los ingresos del hogar. "
                     "Requiere aprobación humana en consola con s o n en 30 segundos; sin respuesta no se aprueba, "
                     "y el mismo motivo no se envía dos veces en una ejecución.",
            "fuente": "src/agente_tramites.py (enviar_solicitud_actualizacion_rsh)",
        },
        {
            "texto": "El asistente no pide RUT ni datos personales, no inventa trámites, montos ni tramos, y solo "
                     "orienta sobre Fonasa y el Registro Social de Hogares. Cada interacción queda en una traza "
                     "JSONL con las herramientas usadas, sus argumentos y las aprobaciones del turno.",
            "fuente": "src/agente_tramites.py (prompt del agente y registrar_traza)",
        },
        {
            "texto": "Cuando el servicio del modelo no responde a tiempo, el cliente reintenta hasta 3 veces con "
                     "espera creciente: 2 segundos, luego 4, con un máximo de 30 y un pequeño jitter aleatorio. "
                     "Si se agotan los intentos, informa que el servicio no respondió y que se intente más tarde.",
            "fuente": "src/cliente.py (con_reintento, consultar_modelo)",
        },
        {
            "texto": "El costo de cada llamada al modelo se estima a partir de totalTokenCount de usageMetadata, "
                     "con una tarifa referencial de 0,002 dólares por cada 1000 tokens, y se acumula en el costo "
                     "total de la sesión mientras el programa sigue corriendo.",
            "fuente": "src/cliente.py (registrar_costo)",
        },
    ]

    texto = "\n\n".join(d["texto"] for d in corpus)

    splitter_fijo = CharacterTextSplitter(
        separator="", chunk_size=110, chunk_overlap=0
    )
    chunks_fijo = splitter_fijo.split_text(texto)

    print("\nCHUNKING FIJO")
    for i, chunk in enumerate(chunks_fijo):
        print(f"--- chunk {i} ({len(chunk)} caracteres) ---")
        print(chunk)

    splitter_recursivo = RecursiveCharacterTextSplitter(
        chunk_size=110, chunk_overlap=20
    )
    chunks_recursivo = splitter_recursivo.split_text(texto)

    print("\nCHUNKING RECURSIVO")
    for i, chunk in enumerate(chunks_recursivo):
        print(f"--- chunk {i} ({len(chunk)} caracteres) ---")
        print(chunk)

    #Recursivo para indexar: cada documento es un párrafo con una idea y no se deben cortar palabras.
    #chunk_size=300 deja casi todos los documentos enteros; overlap 45 = 15% (Bloque 24, lección 2).
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300, chunk_overlap=45
    )
    chunks = splitter.create_documents(
        [d["texto"] for d in corpus],
        metadatas=[{"fuente": d["fuente"]} for d in corpus],  #para citar la fuente en el Bloque 26
    )

    print(f"\nDocumentos originales: {len(corpus)}")
    print(f"Chunks para indexar: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"--- Document {i} ({len(chunk.page_content)} caracteres) ---")
        print(chunk.page_content)

    persist_directory = "vectorstore/"
    modo = input("\nModo (indexar/verificar): ").strip().lower()
    if modo not in ("indexar", "verificar"):
        raise ValueError("Escribe indexar o verificar.")

    #from_documents agrega sobre un índice existente: indexar dos veces duplicaría los chunks.
    if modo == "indexar" and os.path.exists(persist_directory):
        raise ValueError(
            "Ya existe la carpeta del indice. Usa verificar. "
            "Para re-indexar desde cero, borra vectorstore/."
        )

    if modo == "verificar" and not os.path.isdir(persist_directory):
        raise ValueError("No existe la carpeta del indice. Ejecuta primero indexar.")

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        api_key=clave,
    )

    if modo == "indexar":
        try:
            vectorstore = Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                collection_name=coleccion,
                persist_directory=persist_directory,
            )
        except Exception as error:  #solo la llamada externa; from_documents no guarda progreso parcial
            mensaje = str(error)
            if "429" in mensaje or "RESOURCE_EXHAUSTED" in mensaje:
                print("Limite de peticiones alcanzado. Espera un minuto, borra vectorstore/ y vuelve a ejecutar.")
            elif "API key" in mensaje or "401" in mensaje or "403" in mensaje:
                print('La API rechazo tu clave. Revisa API_KEY en tu ".env".')
            else:
                print("No se completo la indexacion:", type(error).__name__)
            raise SystemExit(1) from error

        print(f"Indexados {len(chunks)} chunks en {persist_directory}")

    vectorstore_recargado = Chroma(
        collection_name=coleccion,
        persist_directory=persist_directory,
        embedding_function=embeddings,
    )
    cantidad_guardada = vectorstore_recargado._collection.count()
    print(f"Chunks guardados: {cantidad_guardada}")

    if cantidad_guardada != len(chunks):
        raise ValueError("El conteo guardado no coincide con el corpus actual. Borra vectorstore/ y vuelve a indexar.")

    print("Indice abierto y conteo correcto. La recarga no calcula embeddings.")
