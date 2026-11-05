"""Textos de los prompts. Sin datos personales: la app no pide RUT."""

# Ruta normativa: chain de tres pasos (bloque 18).
EXTRAER_SITUACION = (
    "Resume en dos líneas la situación de esta persona y qué necesita saber. "
    "No agregues información que no esté en la consulta:\n\n{consulta}"
)

REDACTAR_ORIENTACION = (
    "Eres un orientador de trámites de Fonasa y del Registro Social de Hogares en Chile. "
    "A partir de esta situación, explica en un máximo de cuatro oraciones, con lenguaje "
    "sencillo, qué puede hacer la persona y dónde. No pidas RUT ni datos personales:\n\n{situacion}"
)

# Bloque 17: montos y tramos son los errores que f1 no detecta (docs/limites_metricas.md).
REVISAR_ORIENTACION = (
    "Revisa esta orientación para un ciudadano. Corrige el tono si es frío o técnico, "
    "sin agregar información nueva. Agrega [VERIFICAR] justo después de cada monto, "
    "porcentaje o tramo que mencione. Entrega solo el texto final:\n\n{borrador}"
)
