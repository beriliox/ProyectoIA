# Matriz de riesgos de ProyectoIA

Estimaciones didacticas previas a los controles, no probabilidades medidas. BAJO 1-3; MEDIO 4-8; ALTO 9-14; CRITICO 15-25. Los cortes son la convencion del programa.

AL LIMITE indica que variar un punto en P o I cambia la categoria. Cada responsable es un rol que el equipo debe asignar a una persona. Los controles pendientes no se presentan como implementados.

| ID | Riesgo | P | I | Puntaje | Categoria | AL LIMITE |
|---|---|---:|---:|---:|---|---|
| R1 | Un chunk recuperado trae instrucciones que hacen al asistente ignorar sus reglas o revelar el prompt | 4 | 4 | 16 | CRITICO | Si |
| R2 | Datos personales escritos por el usuario quedan guardados completos en trazas o registros | 3 | 5 | 15 | CRITICO | Si |
| R3 | Se activa un cambio del prompt de sistema sin que nadie revise que mantiene sus restricciones | 3 | 4 | 12 | ALTO | Si |
| R4 | El asistente afirma un plazo, monto o tramo que las fuentes recuperadas no respaldan | 3 | 3 | 9 | ALTO | Si |
| R6 | El dataset de clasificacion tiene etiquetas inconsistentes o desbalanceadas y sesgaria un modelo ajustado | 3 | 3 | 9 | ALTO | Si |
| R7 | El agente envia una solicitud de actualizacion a nombre del ciudadano sin su aprobacion | 2 | 4 | 8 | MEDIO | Si |
| R5 | El indice conserva una regla o un canal reemplazado y el asistente responde con datos antiguos | 3 | 2 | 6 | MEDIO | Si |

## R1 Un chunk recuperado trae instrucciones que hacen al asistente ignorar sus reglas o revelar el prompt

**Justificacion**: El corpus puede incorporar texto externo; obedecerlo altera los limites del asistente.

**Mitigacion**: Roles separados, contexto delimitado y descarte por patrones antes de generar; src/logging_rag.py y src/prevencion_prompt_inyection.py (Bloque 31).

**Supervision**: Si se descarta un documento, retener la respuesta hasta que una persona revise la fuente y la corrija o excluya.

**Responsable**: Responsable de seguridad

**Evidencia**: Verificaciones 1 y 3 de src/logging_rag.py; evento documento_descartado_por_inyeccion en docs/logging_rag.jsonl.

**Estado**: Filtro integrado. Revision humana pendiente: hoy solo se registra y la respuesta continua. La lista de patrones se puede evadir.


## R2 Datos personales escritos por el usuario quedan guardados completos en trazas o registros

**Justificacion**: Cualquier persona puede pegar datos personales en una pregunta; los archivos persistentes amplian su exposicion.

**Mitigacion**: src/logging_rag.py registra solo longitud y huella (Bloque 31); la herramienta de notas rechaza RUT; src/agente_tramites.py (Bloque 22).

**Supervision**: Una persona autoriza cada acceso o exportacion de trazas y revisa las ya guardadas.

**Responsable**: Custodio de datos

**Evidencia**: docs/logging_rag.jsonl sin texto de preguntas; test_nota_con_rut_se_rechaza.

**Estado**: Parcial: registrar_traza del agente y src/registro_rag_asistente.py aun guardan la entrada y la respuesta en texto. Control de acceso pendiente.


## R3 Se activa un cambio del prompt de sistema sin que nadie revise que mantiene sus restricciones

**Justificacion**: El prompt se edita en el codigo y un cambio altera las reglas de todo el servicio.

**Mitigacion**: Registro con huella y diff (src/registro_prompts.py) y pausa de LangGraph con aprobacion por consola (src/grafo_supervision.py) (Bloque 32).

**Supervision**: El responsable funcional revisa el diff y aprueba o rechaza en la pausa de grafo_supervision.py antes de activar la version.

**Responsable**: Responsable funcional

**Evidencia**: Ejecucion de src/grafo_supervision.py: interrupt, aprobacion y rechazo en hilos distintos.

**Estado**: Demostrado, no integrado: logging_rag.py no lee la version aprobada. El checkpointer es en memoria.


## R4 El asistente afirma un plazo, monto o tramo que las fuentes recuperadas no respaldan

**Justificacion**: El corpus es limitado y una respuesta inventada puede hacer que el ciudadano pierda un tramite.

**Mitigacion**: Prompt que exige usar solo el contexto, citar y decir cuando no alcanza; src/logging_rag.py (Bloques 26 y 31).

**Supervision**: Revision de una muestra de respuestas contra sus fuentes antes de publicar cambios; las consultas de plazos, montos o tramos se derivan al canal oficial.

**Responsable**: Responsable de contenido

**Evidencia**: Prompt PROMPT_SISTEMA; pregunta de plazo en el paso 4 de src/logging_rag.py, a revisar a mano.

**Estado**: Instruccion integrada. No se validan las citas ni el respaldo; revision humana pendiente.


## R6 El dataset de clasificacion tiene etiquetas inconsistentes o desbalanceadas y sesgaria un modelo ajustado

**Justificacion**: El etiquetado es manual; el entrenamiento reproduciria sus errores.

**Mitigacion**: Balance por tramite y validacion de JSON, claves y duplicados; src/dataset_tuning.py (Bloque 29).

**Supervision**: El responsable de datos revisa ejemplos y balance antes de cualquier envio a entrenamiento.

**Responsable**: Responsable de datos

**Evidencia**: Ejecucion de src/dataset_tuning.py, incluido el dataset roto a proposito.

**Estado**: Validacion lista; no detecta etiquetas contradictorias entre frases parecidas. No se ha entrenado ningun modelo.


## R7 El agente envia una solicitud de actualizacion a nombre del ciudadano sin su aprobacion

**Justificacion**: Es una accion externa e irreversible (hoy simulada) decidida por el modelo.

**Mitigacion**: Aprobacion por consola con tiempo limite dentro de la herramienta; src/agente_tramites.py (Bloque 23).

**Supervision**: esperar_aprobacion: sin un 's' explicito no se envia, y cada decision queda registrada.

**Responsable**: Persona que opera el agente

**Evidencia**: tests/test_agente_tramites.py: rechazada, aprobada una vez y sin consola.

**Estado**: Integrado y probado.


## R5 El indice conserva una regla o un canal reemplazado y el asistente responde con datos antiguos

**Justificacion**: Si el corpus cambia sin reindexar, o queda con menos chunks, permanecen fragmentos obsoletos.

**Mitigacion**: Ids explicitos por chunk y metadata de fuente y fecha; src/rag_indexer_asistente_social.py (Bloques 24 y 25).

**Supervision**: No se pausa cada consulta; se comprueba la fuente antes de reindexar.

**Responsable**: Responsable documental

**Evidencia**: inspeccionar_chunks muestra ids y metadata del indice.

**Estado**: Parcial: los ids reescriben chunks, pero no se eliminan los sobrantes.

