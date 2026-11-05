# Límites de la métrica de evaluación

## Qué mide

La métrica compara las palabras de una respuesta con una referencia,
contando repeticiones después de limpiar y tokenizar ambos textos.
Reporta precisión, cobertura y F1.

Mide cuánto se parece el vocabulario, no si la respuesta es verdadera:
un monto equivocado y uno correcto valen lo mismo, porque cada número
es solo un token más.

## Modos de falla conocidos

- **Montos incorrectos con F1 más alto que respuestas correctas.**
  Un error en las cifras puede puntuar más alto que una respuesta correcta
  redactada con otras palabras, porque el resto de la oración coincide.
  Caso: "¿Quiénes pertenecen al tramo C de Fonasa?".
  Referencia: "Las personas con un ingreso imponible mensual desde $553.554 y menor o igual a $808.187.".
  Respuesta: "Pertenecen al tramo C los trabajadores con un ingreso imponible mensual entre $500.000 y $730.000, o superior si tienen tres o más cargas familiares.".
  F1: 0.359.
  Hallazgo: los dos límites del rango son incorrectos (corrección factual:
  no). Aun así, su F1 supera al del caso de cargas familiares (0.303),
  que es completo y solo omite el 7%. La frase "ingreso imponible mensual" aporta coincidencias
  que esconden el error en las cifras.

- **Paráfrasis correctas penalizadas.**
  Cuando la respuesta dice lo mismo con otras palabras, el F1 queda en
  el grupo más bajo.
  Caso: "¿Cuánto se paga por las cargas familiares en Fonasa?".
  Referencia: "Las cargas familiares no pagan extra; con el 7% de cotización están cubiertas.".
  Respuesta: "Las cargas familiares en Fonasa son totalmente gratuitas y no generan ningún cobro adicional a la cotización mensual del titular.".
  F1: 0.303.
  Hallazgo: la respuesta es completa y solo omite el 7% (corrección
  factual: parcialmente). "No pagan extra" y "no generan ningún cobro
  adicional" significan lo mismo, pero no comparten tokens. Pasa lo mismo
  con "¿Quiénes pueden ser beneficiarios de Fonasa?" (F1 0.381), que es
  correcta pero quedó en el grupo bajo.

- **Un F1 alto no garantiza que estén los datos clave.**
  Caso: "¿Quiénes pertenecen al tramo B de Fonasa?".
  Referencia: "Las personas con un ingreso imponible mensual menor o igual a $553.553.".
  Respuesta: "El tramo B de Fonasa pertenece a los afiliados con un ingreso imponible mensual igual o menor al salario mínimo.".
  F1: 0.563, entre los cinco más altos.
  Hallazgo: la respuesta cambia el monto exacto por "salario mínimo", que
  es justamente el dato que el usuario necesita (completitud: no). La
  cobertura llega a 0.75 porque coincide todo lo demás.

- **No distingue información extra válida de información extra inventada.**
  En ambos casos baja la precisión por igual, sin importar si lo que se
  agregó es cierto.
  Caso A: "¿Quiénes pertenecen al tramo D de Fonasa?", F1 0.118.
  La respuesta agrega "un copago del 20%", que no está en la referencia,
  y omite el monto del rango (corrección factual: no; completitud: no).
  Caso B: "¿Quiénes pertenecen al tramo A de Fonasa?", F1 0.645.
  La respuesta agrega "Subsidio Único Familiar" y el revisor la consideró
  correcta y completa.
  Hallazgo: la métrica no puede saber cuál de los dos agregados es válido.
  En el caso A el puntaje sí fue bajo, pero por la falta de coincidencias,
  no porque haya detectado el dato que no está respaldado.

- **Un dato correcto pero incompleto queda en un puntaje intermedio.**
  Caso: "¿Qué necesito para ingresar al Registro Social de Hogares?".
  Referencia: "Se requiere cédula de identidad vigente y se solicita con ClaveÚnica en línea, en el municipio o en ChileAtiende.".
  Respuesta: "Necesitas tu cédula de identidad vigente y algún documento que acredite tu dirección, como una boleta de servicios básicos.".
  F1: 0.263.
  Hallazgo: el documento principal es correcto, pero falta dónde se hace
  el trámite y agrega un requisito que no está en la referencia (corrección
  factual y completitud: parcialmente). El número solo no permite saber
  si faltan datos o si hay datos erróneos.

## Muestra revisada

Se revisaron 10 casos de un conjunto de 20 respuestas generadas con
`consultar_modelo` (`src/cliente.py`, modelo `gemini-3.5-flash-lite`).
Las métricas están en `docs/resultados_metricas.json`.

La muestra combina los cinco F1 más bajos y los cinco más altos,
seleccionados con `src/revision_manual.py`.

Casos revisados (F1 de menor a mayor):

| ID | F1 | Consulta | Factual | Completa | Contradicción |
|---|---|---|---|---|---|
| 9 | 0.118 | Tramo D de Fonasa | no | no | no |
| 15 | 0.263 | Ingreso al RSH | parcialmente | parcialmente | no |
| 2 | 0.303 | Cargas familiares en Fonasa | parcialmente | sí | no |
| 8 | 0.359 | Tramo C de Fonasa | no | sí | no |
| 1 | 0.381 | Beneficiarios de Fonasa | sí | parcialmente | no |
| 7 | 0.563 | Tramo B de Fonasa | sí | no | no |
| 5 | 0.571 | Cantidad de tramos de Fonasa | sí | sí | no |
| 17 | 0.600 | Qué es un hogar en el RSH | sí | sí | no |
| 18 | 0.609 | Qué es la Cartola Hogar | sí | sí | no |
| 6 | 0.645 | Tramo A de Fonasa | sí | sí | no |

El ID es la posición de la consulta (1 a 20) en la lista `casos`.

Fecha de revisión: 2026-11-04.

Se aplicó la rúbrica de corrección factual, completitud y contradicción,
con una justificación por caso (ver `docs/revision_manual.json`).

**Resultado:** las dos respuestas con errores factuales están en el grupo
bajo, y las cinco del grupo alto son correctas, aunque una está incompleta.
No hubo contradicciones en la muestra, así que este documento no permite
afirmar nada sobre cómo puntúa la métrica una respuesta que contradice a
la referencia. Los 10 casos intermedios (F1 entre 0.409 y 0.556) no se
revisaron.

## Recomendación de uso

**Para qué sirve.** El F1 promedio sirve para comparar versiones del
pipeline (prompt, modelo o `system_instruction`) sobre el mismo conjunto
de 20 consultas. Si el promedio baja, hay que mirar qué casos bajaron.
Con 20 casos, solo deben tomarse en cuenta las diferencias grandes.

**Para qué no sirve.** No debe usarse para aprobar una respuesta
individual. En este dominio, el modo de falla que importa es una cifra
mal dicha (los rangos de los tramos C y D), y la métrica no lo detecta:
el tramo C incorrecto puntuó más que una respuesta correcta.

**Qué revisar a mano:**

- Toda respuesta que contenga montos, porcentajes o rangos de ingreso,
  sin importar su F1. Ejemplos: tramo B (0.563, sin el monto), tramo C
  (0.359, monto erróneo) y tramo D (0.118, copago no respaldado).
- Toda respuesta con F1 bajo 0.40. En la muestra, las dos con errores
  factuales estaban en ese rango, junto con tres respuestas correctas o
  parcialmente correctas, así que ese número solo no distingue unas de otras.
- Toda respuesta con F1 desde 0.56 y sin cifras puede aceptarse sin
  revisión a mano en esta muestra. Ese umbral debe revisarse cuando se
  agreguen casos.