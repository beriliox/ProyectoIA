# Decision de personalizacion

## 1. El problema
El asistente debe clasificar cada mensaje del usuario en un trámite fijo (`fonasa`, `registro_social`, `ingreso`, `nota`, `solicitud`, `fuera_de_alcance`) y responder siempre el JSON `{"tramite": ..., "accion": ...}`. Además, debe orientar con información correcta sobre esos trámites (canales, reglas y límites), que el modelo base no conoce.

Para saber si el formato falla, revisé a mano 20 respuestas del modelo base (`gemini-3.1-flash-lite`, con salida JSON forzada) a mensajes que no están en el dataset. Usé una lista fija de criterios:

1. Es JSON puro, sin texto ni bloque ```` ```json ```` alrededor.
2. Tiene exactamente las claves `tramite` y `accion`.
3. El `tramite` es uno de los seis de la lista.

**Resultado: 0 de 20 respuestas fallan el formato.** Sin forzar la salida JSON, 18 de 20 venían envueltas en ```` ```json ````. Lo que sí falla es la elección del trámite: **7 de 20** eligen uno equivocado. Por ejemplo, dos solicitudes de actualización quedaron como `registro_social` y la pregunta por la pensión garantizada quedó como `ingreso`.

## 2. Resultado del metodo de decision
- RAG: 2 puntos
- PEFT: 1 puntos
- Fine-tuning completo: 0 puntos

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| `informacion_cambia_seguido` | False | `corpus_tramites.txt` |
| `problema_de_formato_o_tono` | False | Revisión a mano: 0 de 20 respuestas fallan el formato (umbral: 3) |
| `dataset_grande_y_de_calidad` | False | 14 ejemplos etiquetados en `dataset_tuning.py` (umbral: 200) |
| `presupuesto_limitado_o_iterar_rapido` | True | Proyecto de curso: 0 dólares para entrenar, y cada intento tardaría de minutos a horas |
| `necesita_multiples_variantes` | False | Un solo asistente, un solo comportamiento |

**Sensibilidad: el resultado es frágil.** Cuatro de las cinco respuestas lo cambian al invertirse:

- Si el formato fallara, o si se necesitaran varias variantes, ganaría PEFT.
- Si hubiera 200 ejemplos, o si no hubiera límite de presupuesto, las tres técnicas empatarían.
- Solo `informacion_cambia_seguido` lo mantiene en RAG.

La respuesta en la que más dudé es la del formato, porque depende de forzar la salida JSON.

## 3. Tecnica elegida y por que
**RAG.** El formato se resuelve con una configuración del modelo (salida JSON forzada), sin entrenar. El problema que queda es de información: el asistente necesita los canales, reglas y límites de `corpus_tramites.txt`, y eso es exactamente lo que hace el RAG que ya está implementado (colección `asistente_social`). PEFT y el fine-tuning completo se descartan: no hay problema de formato que justifique entrenar, hay 14 ejemplos en vez de 200 y no hay presupuesto para entrenamientos.

Hay dos limitaciones del método que conviene dejar escritas:

- **RAG gana solo por el presupuesto.** El método no tiene una pregunta para "al modelo le falta información estable", que es el motivo real para usar RAG en este proyecto.
- **Los 7 errores de clasificación no entran en ninguna pregunta**, porque no son de formato ni de tono. Antes de pensar en tuning, se pueden atacar poniendo en el prompt los 14 ejemplos de `dataset_tuning.py` como ejemplos (*few-shot*), sin entrenar nada.

## 4. Que necesitarias para ejecutarla
- **Corpus:** no falta corpus. `corpus_tramites.txt` ya está indexado (14 chunks). Lo pendiente es lo que mostró la evaluación a la pregunta "¿El asistente me dice en qué tramo quedo?" tiene recall 0.67, porque no recupera `doc_4`, el chunk que dice que el cálculo no asigna tramos.
- **Configuración:** activar la salida JSON forzada (`response_mime_type="application/json"`) en la llamada que clasifica.
- **Clasificación:** probar el prompt con los 14 ejemplos de `dataset_tuning.py`. Se acepta si baja de 7 a menos de 3 errores de trámite en las mismas 20 respuestas.
- **Si algún día gana PEFT:** faltan 46 ejemplos para llegar a 10 por trámite (60 en total). Son 3,83 horas a 5 minutos cada uno, unos $95,83 con el valor de ejemplo del curso de 25 dólares la hora (es un supuesto, no una tarifa real).
