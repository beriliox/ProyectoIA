"""Bloque 32: riesgos del codigo actual y estado explicito de los controles."""
from configuracion import DOCS, guardar_json

RIESGOS = [
    {"id": "R1",
     "riesgo": "Un chunk recuperado trae instrucciones que hacen al asistente ignorar sus reglas o revelar el prompt",
     "probabilidad": 4,
     "impacto": 4,
     "justificacion": "El corpus puede incorporar texto externo; obedecerlo altera los limites del asistente.",
     "mitigacion": "Roles separados, contexto delimitado y descarte por patrones antes de generar; src/logging_rag.py y src/prevencion_prompt_inyection.py (Bloque 31).",
     "supervision": "Si se descarta un documento, retener la respuesta hasta que una persona revise la fuente y la corrija o excluya.",
     "responsable": "Responsable de seguridad",
     "evidencia": "Verificaciones 1 y 3 de src/logging_rag.py; evento documento_descartado_por_inyeccion en docs/logging_rag.jsonl.",
     "estado": "Filtro integrado. Revision humana pendiente: hoy solo se registra y la respuesta continua. La lista de patrones se puede evadir."},
    {"id": "R2",
     "riesgo": "Datos personales escritos por el usuario quedan guardados completos en trazas o registros",
     "probabilidad": 3,
     "impacto": 5,
     "justificacion": "Cualquier persona puede pegar datos personales en una pregunta; los archivos persistentes amplian su exposicion.",
     "mitigacion": "src/logging_rag.py registra solo longitud y huella (Bloque 31); la herramienta de notas rechaza RUT; src/agente_tramites.py (Bloque 22).",
     "supervision": "Una persona autoriza cada acceso o exportacion de trazas y revisa las ya guardadas.",
     "responsable": "Custodio de datos",
     "evidencia": "docs/logging_rag.jsonl sin texto de preguntas; test_nota_con_rut_se_rechaza.",
     "estado": "Parcial: registrar_traza del agente y src/registro_rag_asistente.py aun guardan la entrada y la respuesta en texto. Control de acceso pendiente."},
    {"id": "R3",
     "riesgo": "Se activa un cambio del prompt de sistema sin que nadie revise que mantiene sus restricciones",
     "probabilidad": 3,
     "impacto": 4,
     "justificacion": "El prompt se edita en el codigo y un cambio altera las reglas de todo el servicio.",
     "mitigacion": "Registro con huella y diff (src/registro_prompts.py) y pausa de LangGraph con aprobacion por consola (src/grafo_supervision.py) (Bloque 32).",
     "supervision": "El responsable funcional revisa el diff y aprueba o rechaza en la pausa de grafo_supervision.py antes de activar la version.",
     "responsable": "Responsable funcional",
     "evidencia": "Ejecucion de src/grafo_supervision.py: interrupt, aprobacion y rechazo en hilos distintos.",
     "estado": "Demostrado, no integrado: logging_rag.py no lee la version aprobada. El checkpointer es en memoria."},
    {"id": "R4",
     "riesgo": "El asistente afirma un plazo, monto o tramo que las fuentes recuperadas no respaldan",
     "probabilidad": 3,
     "impacto": 3,
     "justificacion": "El corpus es limitado y una respuesta inventada puede hacer que el ciudadano pierda un tramite.",
     "mitigacion": "Prompt que exige usar solo el contexto, citar y decir cuando no alcanza; src/logging_rag.py (Bloques 26 y 31).",
     "supervision": "Revision de una muestra de respuestas contra sus fuentes antes de publicar cambios; las consultas de plazos, montos o tramos se derivan al canal oficial.",
     "responsable": "Responsable de contenido",
     "evidencia": "Prompt PROMPT_SISTEMA; pregunta de plazo en el paso 4 de src/logging_rag.py, a revisar a mano.",
     "estado": "Instruccion integrada. No se validan las citas ni el respaldo; revision humana pendiente."},
    {"id": "R5",
     "riesgo": "El indice conserva una regla o un canal reemplazado y el asistente responde con datos antiguos",
     "probabilidad": 3,
     "impacto": 2,
     "justificacion": "Si el corpus cambia sin reindexar, o queda con menos chunks, permanecen fragmentos obsoletos.",
     "mitigacion": "Ids explicitos por chunk y metadata de fuente y fecha; src/rag_indexer_asistente_social.py (Bloques 24 y 25).",
     "supervision": "No se pausa cada consulta; se comprueba la fuente antes de reindexar.",
     "responsable": "Responsable documental",
     "evidencia": "inspeccionar_chunks muestra ids y metadata del indice.",
     "estado": "Parcial: los ids reescriben chunks, pero no se eliminan los sobrantes."},
    {"id": "R6",
     "riesgo": "El dataset de clasificacion tiene etiquetas inconsistentes o desbalanceadas y sesgaria un modelo ajustado",
     "probabilidad": 3,
     "impacto": 3,
     "justificacion": "El etiquetado es manual; el entrenamiento reproduciria sus errores.",
     "mitigacion": "Balance por tramite y validacion de JSON, claves y duplicados; src/dataset_tuning.py (Bloque 29).",
     "supervision": "El responsable de datos revisa ejemplos y balance antes de cualquier envio a entrenamiento.",
     "responsable": "Responsable de datos",
     "evidencia": "Ejecucion de src/dataset_tuning.py, incluido el dataset roto a proposito.",
     "estado": "Validacion lista; no detecta etiquetas contradictorias entre frases parecidas. No se ha entrenado ningun modelo."},
    {"id": "R7",
     "riesgo": "El agente envia una solicitud de actualizacion a nombre del ciudadano sin su aprobacion",
     "probabilidad": 2,
     "impacto": 4,
     "justificacion": "Es una accion externa e irreversible (hoy simulada) decidida por el modelo.",
     "mitigacion": "Aprobacion por consola con tiempo limite dentro de la herramienta; src/agente_tramites.py (Bloque 23).",
     "supervision": "esperar_aprobacion: sin un 's' explicito no se envia, y cada decision queda registrada.",
     "responsable": "Persona que opera el agente",
     "evidencia": "tests/test_agente_tramites.py: rechazada, aprobada una vez y sin consola.",
     "estado": "Integrado y probado."},
]


def puntaje_riesgo(probabilidad, impacto):
    if any(type(n) is not int or not 1 <= n <= 5 for n in (probabilidad, impacto)):
        raise ValueError("P e I deben ser enteros entre 1 y 5")
    return probabilidad * impacto


def categoria_riesgo(puntaje):
    if puntaje >= 15:
        return "CRITICO"
    if puntaje >= 9:
        return "ALTO"
    if puntaje >= 4:
        return "MEDIO"
    return "BAJO"


def esta_en_el_limite(probabilidad, impacto):
    actual = categoria_riesgo(puntaje_riesgo(probabilidad, impacto))
    vecinos = [(probabilidad + 1, impacto), (probabilidad - 1, impacto),
               (probabilidad, impacto + 1), (probabilidad, impacto - 1)]
    return any(categoria_riesgo(p * i) != actual for p, i in vecinos if 1 <= p <= 5 and 1 <= i <= 5)


def completar_matriz():
    filas = []
    for riesgo in RIESGOS:
        fila = dict(riesgo)
        fila["puntaje"] = puntaje_riesgo(fila["probabilidad"], fila["impacto"])
        fila["categoria"] = categoria_riesgo(fila["puntaje"])
        fila["al_limite"] = esta_en_el_limite(fila["probabilidad"], fila["impacto"])
        filas.append(fila)
    return sorted(filas, key=lambda r: -r["puntaje"])


def main():
    filas = completar_matriz()
    guardar_json(DOCS / "matriz_riesgos.json", filas)
    lineas = ["# Matriz de riesgos de ProyectoIA", "",
              "Estimaciones didacticas previas a los controles, no probabilidades medidas. BAJO 1-3; MEDIO 4-8; ALTO 9-14; CRITICO 15-25. Los cortes son la convencion del programa.", "",
              "AL LIMITE indica que variar un punto en P o I cambia la categoria. Cada responsable es un rol que el equipo debe asignar a una persona. Los controles pendientes no se presentan como implementados.", "",
              "| ID | Riesgo | P | I | Puntaje | Categoria | AL LIMITE |",
              "|---|---|---:|---:|---:|---|---|"]
    for r in filas:
        lineas.append(f"| {r['id']} | {r['riesgo']} | {r['probabilidad']} | {r['impacto']} | {r['puntaje']} | {r['categoria']} | {'Si' if r['al_limite'] else 'No'} |")
    for r in filas:
        lineas.extend(["", f"## {r['id']} {r['riesgo']}", ""])
        for campo in ("justificacion", "mitigacion", "supervision", "responsable", "evidencia", "estado"):
            lineas.append(f"**{campo.capitalize()}**: {r[campo]}\n")
    (DOCS / "matriz_riesgos.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    for r in filas:
        print(r["id"], r["categoria"], r["puntaje"], "AL LIMITE" if r["al_limite"] else "")


if __name__ == "__main__":
    main()