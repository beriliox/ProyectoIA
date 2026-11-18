from rag_indexer import cargar_vectorstore

def precision_at_k(ids_recuperados: list[str], ids_relevantes: set[str]) -> float:
    """
    id_recuperados los que me trajo el retriever
    De los 'k' chunks que me trajo el retriever, ¿qué fracción realmente sirve?
    Devuelve 0.0 si el retriever no devolvió ningún id
    """
    if not ids_recuperados:
      return 0.0
    
    # Recorro uno por uno cada ID que devolvió el retriever, si acaso existe en id_relevantes lo agrego a la lista de acertados
    acertados = [i for i in ids_recuperados if i in ids_relevantes]
    
    return len(acertados) / len(ids_recuperados)

def recall_at_k(ids_recuperados: list[str], ids_relevantes: set[str]) -> float | None:
    """
    De todos los chunks relevantes que existen en mi corpus, ¿qué fracción logré rescatar?
    Devuelve None si la pregunta no tiene respuesta en corpus (ids_relevantes es vacío)
    """
    if not ids_relevantes:
        return None

    acertados = [i for i in ids_recuperados if i in ids_relevantes]
    return len(acertados) / len(ids_relevantes)

def f1_score(precision: float, recall: float | None) -> float:
    """
    MEDIA ARMÓNICA ENTRE PRECISION Y EXHAUSTIVIDAD: EQUILIBRIO ENTRE AMBOS PARA COMPARAR
    CONFIGURACIONES DISTINTAS DE K O CHUNK_SIZE.
    """
    if recall is None or (precision + recall) == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)

def evaluar_recuperacion(retriever, casos: list[dict], k: int = 3):
    """
    Correr cada caso del conjunto de evaluaciones contra el retriever real de Chroma
    y va a calcular precisión, recall y F1
    """
    resultados = []
    for caso in casos:
      #1. Consultamos al retriever, cuáles son los chunks que me regresa la invocación. SI GASTA TOKENS
      chunks = retriever.invoke(caso["pregunta"])

      #2. Extraer los IDs
      ids_recuperados = [c.id for c in chunks]

      #3. Calculamos las metricas
      p = precision_at_k(ids_recuperados, caso["ids_relevantes"])
      r = recall_at_k(ids_recuperados, caso["ids_relevantes"])
      f1 = f1_score(p, r)

      #4. Agregar esas metricas a los resultados
      resultados.append({
          "pregunta": caso["pregunta"],
          "ids_recuperados": caso["ids_recuperados"],
          "precision": p,
          "recall": r,
          "f1": f1
      })

    return resultados

if __name__ == "__main__": 
    CARPETA_DB = "vectorstore_ejemplo"
    K = 3
    
    vs = cargar_vectorstore(CARPETA_DB)

    # pregunta = "¿Cuáles son los errores de credenciales inválidas?"
    # ids_relevantes = {"0784ca51-12e6-452a-8500-6133bdd7a036", "bc680ad3-90a6-411e-ab93-b14be598feff", "1610938d-a90e-4332-87d9-e512f5874b5e"}

    # retriever = vs.as_retriever(search_kwargs={"k": K})
    # chunks = retriever.invoke(pregunta)
    # print(chunks)
    # ids_recuperados = [c.id for c in chunks]

    # precision = precision_at_k(ids_recuperados, ids_relevantes)
    # print("Precision: ", precision)

    # exhaustividad = recall_at_k(ids_recuperados, ids_relevantes)
    # print("Exhaustividad: ", exhaustividad)

    # f1 = f1_score(precision, exhaustividad)
    # print("F1 Score: ", f1)

    casos_evaluacion = [
        {"pregunta": "que hace el cliente si una llamada tarda demasiado", "ids_relevantes": {"doc0"}},
        {"pregunta": "que pasa si la clave de api es invalida",            "ids_relevantes": {"doc1"}},
        {"pregunta": "como se calcula el costo de una llamada",            "ids_relevantes": {"doc2"}},
        {"pregunta": "como decide el agente que herramienta usar",         "ids_relevantes": {"doc3"}},
    ]