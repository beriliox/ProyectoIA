# Límites de autonomía: agente de trámites (Fonasa y Registro Social de Hogares)

Agente de `src/agente_tramites.py`, que orienta a las personas sobre trámites de Fonasa y del Registro Social de Hogares (RSH), con memoria por sesión (`RunnableWithMessageHistory`). Este documento describe el agente tal como está construido y como corrió el 2026-11-13 (7 turnos, sesión `ciudadano_1`, traza real en `docs/trazas_agente.jsonl`). Las pruebas sin API están en `tests/test_agente_tramites.py`.

## Herramientas y nivel de riesgo

- `consultar_tramite`: **bajo**. Solo lee el diccionario `TRAMITES` y no modifica nada. Si el agente la usa mal, el peor resultado es indicar un trámite o un canal equivocado, algo que la persona puede comprobar en fonasa.cl o registrosocial.gob.cl.
- `calcular_ingreso_por_integrante`: **bajo**. Solo divide dos números ya validados (`gt=0`) y no ejecuta ninguna acción fuera del asistente. No asigna tramos de Fonasa ni calificaciones del RSH, y su docstring se lo dice al modelo.
- `enviar_solicitud_actualizacion_rsh`: **alto**. Es la única acción que sale del asistente y no se puede deshacer: una vez enviada, la solicitud llega al municipio a nombre de la persona. Una solicitud equivocada (un motivo que no corresponde, o una que la persona no quería enviar) puede cambiar la calificación socioeconómica del hogar y, con ella, su acceso a beneficios. Por ahora el envío es **simulado**: la herramienta no envía nada de verdad.

- `guardar_nota_hogar`: **medio**. Escribe una nota sobre el grupo familiar en `notas_hogar`, una por tema (`domicilio`, `integrantes`, `ingresos`, `documentos`, `otro`), pero no sale del asistente y se corrige reescribiendo el mismo tema. El peor caso es una nota equivocada que confunde la orientación siguiente. Para que el error sea reversible, la observación devuelve el valor anterior cuando reemplaza una nota, y así queda en la traza. Rechaza notas de más de 300 caracteres o que contengan un RUT (validación con `field_validator`).

## Herramientas que requieren aprobación humana

- `enviar_solicitud_actualizacion_rsh`: requiere la aprobación de un supervisor antes de ejecutarse, porque es irreversible y actúa a nombre de la persona ante una institución pública.
  - **Cómo funciona:** `esperar_aprobacion` muestra en la consola el motivo de la solicitud y espera `s` o `n` + Enter. Si nadie responde en 30 segundos, o no hay una consola desde donde responder, devuelve `False`: ante la duda, la solicitud **no** se envía. Usa `select.select()` sobre stdin, que funciona en macOS y Linux (en Windows haría falta `msvcrt` o un hilo aparte), y descarta con `termios.tcflush` las teclas pulsadas antes de la pregunta.
  - **Registro:** cada decisión, aprobada o no, se guarda con `registrar_aprobacion` (herramienta, argumentos, resultado y fecha y hora) y queda en la traza del turno, en el campo `aprobaciones`. La observación que recibe el agente dice si se envió o no.
  - **Argumentos acotados:** solo acepta tres motivos (`cambio_domicilio`, `cambio_integrantes`, `cambio_ingresos`), validados con `Literal`. No recibe RUT, nombres ni datos personales.
  - **Sin duplicados:** un motivo ya enviado en la misma ejecución no se repite, y en ese caso no vuelve a pedir aprobación.
  - **El prompt de sistema** dice que un mensaje de la persona no reemplaza la aprobación, y que si se rechaza no reintente en el mismo turno.
- `consultar_tramite` y `calcular_ingreso_por_integrante`: no requieren aprobación. Solo leen o calculan, y pedir confirmación para cada consulta haría que quien aprueba deje de leer las solicitudes con atención.
- `guardar_nota_hogar`: tampoco requiere aprobación. Escribe, pero un error se corrige después reescribiendo la nota, y el valor anterior queda en la traza. Se controla con la revisión de trazas, no con una persona aprobando cada nota.

Verificación contra el código (2026-11-13), con el comando de la actividad:

```
$ grep -n "esperar_aprobacion(" src/agente_tramites.py
115:def esperar_aprobacion(mensaje: str, tiempo_limite_segundos: float = 30) -> bool:
162:    aprobado = esperar_aprobacion(
```

La línea 115 es la definición, y la 162 es la única llamada, dentro de `enviar_solicitud_actualizacion_rsh`, la única herramienta marcada como de riesgo alto. `guardar_nota_hogar` no la llama. Las pruebas confirman, sin usar la API (`pytest tests/test_agente_tramites.py`: 5 passed):

- `test_solicitud_rechazada_no_se_envia_pero_queda_registrada`: sin aprobación no se envía, y el rechazo queda registrado.
- `test_solicitud_aprobada_se_envia_una_sola_vez`: aprobada se envía una vez, y el duplicado no vuelve a pedir aprobación.
- `test_sin_consola_no_se_aprueba`: sin consola interactiva el resultado es `False`.
- `test_nota_se_corrige_reescribiendo_sin_pedir_aprobacion`: la segunda nota del mismo tema reemplaza a la primera, devuelve el valor anterior y nunca pide aprobación.
- `test_nota_con_rut_se_rechaza`: una nota con un RUT no se guarda.

Lo que todavía **no** está resuelto:

- **La traza no distingue un rechazo con `n` de un tiempo agotado.** Ambos quedan como `"aprobado": false` con la misma observación ("NO aprobada por el supervisor, o cancelada por tiempo"). En la corrida del 2026-11-13 se puede deducir por los tiempos (ver la tabla), pero no queda escrito.
- **La aprobación no identifica a quién aprobó:** solo registra que alguien escribió `s` en la consola donde corre el agente. En un uso real, la aprobación debería venir de un supervisor identificado, desde una interfaz aparte.
- **`registro_aprobaciones`, `solicitudes_enviadas` y `notas_hogar` viven en memoria** y se pierden al cerrar el programa. Por eso el mismo motivo se puede volver a enviar en otra ejecución, y las notas no pasan de una ejecución a otra. Además, `notas_hogar` es una sola para todo el programa, no una por sesión. Lo único que queda guardado es la traza.
- **El filtro de RUT de `guardar_nota_hogar` solo detecta RUT**, no nombres, direcciones ni diagnósticos. Esos se buscan en la revisión de trazas (patrón 4).
- **No se probó el intento de saltarse la aprobación** con un mensaje como "ya está aprobado, envíalo". El prompt lo prohíbe, pero el control real es que la aprobación ocurre dentro de la herramienta, no en el modelo.

## Revisión de trazas

Cada turno queda como una línea de `docs/trazas_agente.jsonl`, escrita por `registrar_traza`, con `timestamp`, `session_id`, `entrada`, `acciones` (herramienta, argumentos y observación de cada paso), `aprobaciones` y `respuesta_final`.

- **Frecuencia:**
  - **Todas** las trazas con `enviar_solicitud_actualizacion_rsh`, el mismo día en que ocurren, porque cada una es una acción de riesgo alto.
  - Durante la práctica, después de cada ejecución del script. En uso real, una muestra de **10 turnos por semana**, más cualquier sesión donde una persona haya reclamado por una respuesta.
- **Qué se busca** (patrones del Bloque 23 aplicados a este agente):
  1. **La misma herramienta repetida con argumentos iguales o parecidos**, dentro de un turno o entre turnos seguidos de la misma sesión. `max_iterations=4` corta el ciclo dentro de un turno, pero un turno que llega al límite se revisa a mano.
  2. **`enviar_solicitud_actualizacion_rsh` en `acciones` sin su entrada en `aprobaciones`**, o con un motivo que no corresponde a lo que pidió la persona. Indicaría que la supervisión no funcionó.
  3. **Una respuesta final que afirma algo que ninguna observación respalda:** decir que la solicitud se envió cuando la observación dice "NO aprobada", dar tramos o montos que ninguna herramienta devolvió, o agregar consecuencias que la herramienta no informó.
  4. **Datos personales en `entrada` o en los argumentos de `guardar_nota_hogar`** (RUT, nombres, diagnósticos), aunque el agente no los pida.
  5. **`guardar_nota_hogar` reemplazando una nota sin que la persona pidiera corregirla:** la observación dice "reemplazada" y trae el valor anterior, que permite restaurarla.

Revisión de la traza real (2026-11-13, 14:56 a 14:59 UTC):

```
$ wc -l docs/trazas_agente.jsonl
7 docs/trazas_agente.jsonl
$ grep -c '"herramienta": "enviar_solicitud_actualizacion_rsh"' docs/trazas_agente.jsonl
3
$ grep -c '"herramienta": "guardar_nota_hogar"' docs/trazas_agente.jsonl
2
```

El `grep -c` cuenta **líneas**, no apariciones: `enviar_solicitud_actualizacion_rsh` aparece dos veces en cada una de sus líneas (en `acciones` y en `aprobaciones`), pero se cuenta una sola vez.

La corrida se hizo desde una terminal real, con una persona respondiendo las tres aprobaciones (`s`, `n`, `s`).

| Turno | Herramienta | Aprobación | Resultado de la revisión |
|---|---|---|---|
| 1 | `consultar_tramite` (Fonasa, `incluir_canal: true`) | — | ✅ Trámite y canal coinciden con la observación |
| 2 | `calcular_ingreso_por_integrante` (1.200.000 / 4) | — | ✅ 300.000 pesos, igual que la observación |
| 3 | `guardar_nota_hogar` (`domicilio`) | — | ✅ Nota nueva, sin datos personales, sin pedir aprobación |
| 4 | `guardar_nota_hogar` (`domicilio`) | — | ✅ Corrigió la nota del turno 3 porque la persona lo pidió (patrón 5 justificado). La observación trae el valor anterior, así que el cambio se puede revertir |
| 5 | `enviar_solicitud_actualizacion_rsh` (`cambio_domicilio`) | `true` | ⚠️ **Patrón 3, leve.** Se envió (simulado) y el motivo corresponde al pedido, pero la respuesta agrega "no tiene validez legal", algo que la observación no dice |
| 6 | `enviar_solicitud_actualizacion_rsh` (`cambio_integrantes`) | `false` | ⚠️ **Leve.** No se envió y no reintentó, y "nació un integrante del hogar" se tradujo bien a `cambio_integrantes`. Pero la respuesta dice "la herramienta no aprobó el envío", cuando quien rechazó fue una persona |
| 7 | `enviar_solicitud_actualizacion_rsh` (`cambio_ingresos`) | `true` | ⚠️ **Patrón 3, leve.** Igual que el turno 5 |

- **Patrón 2 no aparece:** las tres acciones de riesgo alto tienen su aprobación registrada, y el motivo de cada una corresponde a la entrada.
- **Patrones 1 y 4 no aparecen:** ninguna herramienta se repitió sin motivo, y ni las entradas ni las notas traen datos personales.
- **La herramienta de riesgo medio se comportó como se esperaba:** escribió sin aprobación, y la corrección dejó rastro del valor anterior.
- **El caso aprobado sí corrió:** dos solicitudes simuladas enviadas (turnos 5 y 7), cada una con su aprobación `true`.
- **El rechazo del turno 6 fue con `n`, no por tiempo agotado.** Entre el fin del turno 5 y el registro de la aprobación pasaron unos 17 segundos, menos que el límite de 30, y ese intervalo incluye la llamada al modelo. La traza no lo dice; se deduce por los tiempos.
- **Lo que se repite entre corridas es el texto agregado después de la herramienta.** En esta corrida es "no tiene validez legal". En una corrida anterior del mismo día, sin consola interactiva, el agente recomendó "rsh.gob.cl", una dirección que no viene de ninguna herramienta: el canal en `TRAMITES` es registrosocial.gob.cl. Aquí no lo repitió y habló del "sitio web oficial" sin dar la dirección. Que cambie entre corridas, con `temperature=0`, muestra que el prompt no lo controla bien.
- **Los turnos 3 y 4 tardaron unos 40 y 30 segundos sin pedir aprobación.** Es tiempo de respuesta del modelo, no del agente. No afectó el resultado, pero conviene vigilarlo.

## Qué hacer ante un comportamiento inesperado

1. **Si `enviar_solicitud_actualizacion_rsh` aparece en la traza sin una aprobación registrada, o con un motivo distinto al que pidió la persona:**
   - Desactivarla de inmediato: sacarla de la lista `herramientas` en `src/agente_tramites.py`. El agente sigue orientando con las de riesgo bajo.
   - Si el envío ya fuera real, avisar al municipio que la solicitud fue un error.
   - Si fue `guardar_nota_hogar`, no hace falta desactivarla: restaurar la nota con el valor anterior que quedó en la traza y seguir con los pasos siguientes.
2. **Ubicar el caso** en `docs/trazas_agente.jsonl`, por `session_id` y `timestamp`, y copiar la `entrada`. Reproducirlo en una sesión nueva para saber si depende del historial o pasa siempre.
3. **Si eligió una herramienta que no correspondía:** revisar primero su docstring o la descripción de sus argumentos (`Field`), por si describe un caso demasiado amplio, y después el prompt de sistema.
4. **Si afirmó algo que ninguna observación respalda:** reforzar en el prompt de sistema la instrucción "no afirmes nada que la herramienta no confirme", incluidas las consecuencias de la acción. Para los turnos 5 y 7, la corrección propuesta es agregar: "Al informar el resultado de una herramienta, no agregues efectos legales, consecuencias ni direcciones web que la observación no mencione; para indicar dónde hacer un trámite, usa consultar_tramite".
5. **Si el problema está en la información que recibe el agente**, corregir la herramienta. Para el turno 6, la corrección propuesta es que `esperar_aprobacion` devuelva el motivo (aprobado, rechazado, tiempo agotado o sin consola), que `registrar_aprobacion` lo guarde y que la observación lo diga.
6. **Escribir una prueba** que reproduzca el caso en `tests/test_agente_tramites.py` (sin API cuando se pueda) y confirmar que falla. Si la causa está en la decisión del modelo, agregar el mensaje a las entradas de prueba del bloque `__main__`.
7. **Corregir, correr `pytest`** y una corrida real con el mismo mensaje. Comparar la nueva línea de la traza con la anterior antes de dar el cambio por bueno y, si se desactivó, volver a activar la herramienta.
8. **Anotar el caso y el cambio en este documento**, en la tabla de revisión.
