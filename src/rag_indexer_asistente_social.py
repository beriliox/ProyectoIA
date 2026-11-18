from dotenv import load_dotenv #importa variables de entorno
from langchain_text_splitters import RecursiveCharacterTextSplitter #función para dividir (chunking)
from langchain_google_genai import GoogleGenerativeAIEmbeddings #embedding de Gemini
from langchain_chroma import Chroma #Chroma = vector store
from langchain_core.documents import Document

load_dotenv()

"""
Recibir un corpus/texto dividirlo, calcular el embedding, y guardar el corpus en mi vector store
"""
def indexar_corpus(corpus, persist_directory, collection_name, chunk_size=300, chunk_overlap=45):
    #Dividir en fragmentos más pequeños corpus/texto
    splitter = RecursiveCharacterTextSplitter( #Configuración para la división
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    #División
    chunks = splitter.split_documents(corpus)

    #Crear los ids
    ids = [f"doc_{i}" for i in range(len(chunks))] #["doc_0", "doc_1", "doc_2"]

    #Embedding
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    #Si esta función recibe ids, actualizar los ids que ya existían y generar un nuevo chunk para aquellos que no
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory,
        collection_name=collection_name,
        ids=ids
    )

    return vector_store

"""
Función que abre/carga la carpeta existente del disco para leerla. NO GASTO TOKENS
"""
def cargar_vectorstore(persist_directory, collection_name):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    return Chroma(persist_directory=persist_directory, embedding_function=embeddings, collection_name=collection_name)

#¿Cuál es el ID de cada chunk?
def inspeccionar_chunks(vectorstore):
    datos = vectorstore.get()
    total = len(datos["ids"])
    print(f"-- INVENTARIO DE CHUNKS EN CHROMA (Total: {total}) --")

    for i, (chunk_id, texto, meta) in enumerate(zip(datos["ids"], datos["documents"], datos["metadatas"]), start=1):
        print(f"[{i}] ID: {chunk_id}")
        print(f"Fuente/Meta: {meta}")
        resumen = texto.replace("\n", " ")[:100] #Quita los saltos de línea y obten solo los primeros 100 caracteres
        print(f"Contenido: {resumen}...")

if __name__ == "__main__":
    #Constantes
    CARPETA_DB = "vectorstore"
    COLECCION = "asistente_social"

    vs = cargar_vectorstore(CARPETA_DB, COLECCION)

    with open("corpus_tramites.txt", "r", encoding="utf-8") as f: #r: read, a: append, w: write
        contenido = f.read()

    documentos = [Document(page_content=contenido, metadata={"fuente": "corpus_tramites.txt", "fecha": "2026-11-17"})]

    #indexar_corpus(documentos, CARPETA_DB, COLECCION) #comentado para no volver a gastar tokens en cada ejecución

    inspeccionar_chunks(vs)
