from datetime import datetime
from evaluador_rag import precision_at_k, recall_at_k, f1_score
from rag_indexer_asistente_social import cargar_vectorstore

def evaluar_recuperacion(retriever, casos: list[dict]):
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
            "ids_recuperados": ids_recuperados,
            "precision": p,
            "recall": r,
            "f1": f1
        })

    return resultados

if __name__ == "__main__":
    CARPETA_DB = "vectorstore"
    COLECCION = "asistente_social"
    K = 3

    vs = cargar_vectorstore(CARPETA_DB, COLECCION)
    retriever = vs.as_retriever(search_kwargs={"k": K})

    #Ids etiquetados leyendo los chunks de corpus_tramites.txt, antes de correr el retriever
    casos_evaluacion = [
        {"pregunta": "¿Dónde actualizo mi tramo de Fonasa?", "ids_relevantes": {"doc_1"}},
        {"pregunta": "¿En qué sitio actualizo los datos de mi hogar en el registro social?", "ids_relevantes": {"doc_2"}},
        {"pregunta": "Somos cinco en la casa, ¿cómo se saca lo que gana cada uno?", "ids_relevantes": {"doc_3"}},
        {"pregunta": "¿El asistente me dice en qué tramo quedo?", "ids_relevantes": {"doc_4", "doc_9", "doc_10"}},
        {"pregunta": "¿Puedo corregir algo que anoté sobre mi familia?", "ids_relevantes": {"doc_5"}},
        {"pregunta": "¿Puedo poner mi RUT en una nota?", "ids_relevantes": {"doc_6", "doc_9"}},
        {"pregunta": "¿Por qué motivos puedo pedir que actualicen mi registro social?", "ids_relevantes": {"doc_7", "doc_8"}},
        {"pregunta": "¿Quién tiene que autorizar el envío de una solicitud?", "ids_relevantes": {"doc_8"}},
        {"pregunta": "¿Puedo mandar dos veces la misma solicitud?", "ids_relevantes": {"doc_8"}},
        {"pregunta": "¿Qué pasa si el servicio se demora en contestar?", "ids_relevantes": {"doc_11", "doc_12"}},
        {"pregunta": "¿Cuánto cuesta cada consulta al modelo?", "ids_relevantes": {"doc_13"}},
        {"pregunta": "¿Queda registro de lo que pregunto?", "ids_relevantes": {"doc_10"}},
    ]

    resultados = evaluar_recuperacion(retriever, casos_evaluacion)

    precision_promedio = sum(r["precision"] for r in resultados) / len(resultados)
    recall_promedio = sum(r["recall"] for r in resultados) / len(resultados)

    for r in resultados:
        print(f"{r['precision']:.2f}  {r['recall']:.2f}  {r['f1']:.2f}  {r['pregunta']} -> {r['ids_recuperados']}")
    print(f"\npromedio -> precision: {precision_promedio:.3f}  recall: {recall_promedio:.3f}")

    #"w" sobrescribe el archivo en cada corrida
    with open("docs/resultados_evaluacion.txt", "w", encoding="utf-8") as archivo:
        archivo.write(f"Fecha: {datetime.now():%Y-%m-%d %H:%M}\n")
        archivo.write(f"Configuracion: k={K}, chunk_size=300, chunk_overlap=45, coleccion={COLECCION}\n\n")
        for r in resultados:
            archivo.write(f"{r['precision']:.2f}  {r['recall']:.2f}  {r['f1']:.2f}  {r['pregunta']} -> {r['ids_recuperados']}\n")
        archivo.write(f"\npromedio -> precision: {precision_promedio:.3f}  recall: {recall_promedio:.3f}\n")