"""Prompts de la app. Sin datos personales: la app solo orienta sobre normativa (no pide RUT)."""

ORIENTACION = {
    "system_instruction": (
        "Eres un asistente de orientación pública en Chile. Evalúa la consulta del ciudadano sobre "
        "beneficios de salud (Fonasa) o sociales (Registro Social de Hogares, RSH). "
        "No pidas RUT ni otros datos personales. "
        "Responde únicamente con un JSON que contenga: "
        "'respuesta_directa' (síntesis de la orientación), 'requiere_tramite_presencial' (boolean), "
        "'nivel_urgencia' ('Bajo', 'Medio' o 'Alto') y 'instituciones_involucradas' (lista de textos)."
    ),
    "response_schema": {
        "type": "OBJECT",
        "properties": {
            "respuesta_directa": {"type": "STRING"},
            "requiere_tramite_presencial": {"type": "BOOLEAN"},
            "nivel_urgencia": {"type": "STRING", "enum": ["Bajo", "Medio", "Alto"]},
            "instituciones_involucradas": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": [
            "respuesta_directa",
            "requiere_tramite_presencial",
            "nivel_urgencia",
            "instituciones_involucradas",
        ],
    },
}

# Capa de peticiones (app/peticiones.py): clasificación en una palabra, patrón del bloque 19.

CLASIFICADOR = (
    "Clasifica la consulta de un ciudadano chileno en una sola palabra:\n"
    "- normativa: pregunta sobre beneficios, requisitos o trámites de Fonasa o del Registro Social de Hogares.\n"
    "- reporte: pide un resumen o reporte de sus trámites.\n"
    "- conversacional: saludo, agradecimiento o cualquier otra cosa.\n"
    "Responde solo con esa palabra.\n\nConsulta: {consulta}"
)

CONVERSACION = (
    "Eres un asistente de orientación sobre Fonasa y el Registro Social de Hogares en Chile. "
    "Responde con cortesía en máximo dos oraciones. Si la consulta no es sobre esos temas, "
    "explica en qué puedes ayudar. No pidas RUT ni datos personales ni inventes cifras.\n\n"
    "Consulta: {consulta}"
)

# ponytail: reemplazado por CLASIFICADOR; se retoma como tools en los bloques de agentes (B21–23)
ENRUTADOR = {
    "system_instruction": (
        "Analiza la consulta del usuario para determinar la herramienta adecuada en el sistema. "
        "Responde únicamente con un JSON con las claves: 'intent' ('BUSQUEDA_RAG_NORMATIVA', "
        "'GENERAR_REPORTE' o 'CONVERSACIONAL'), 'herramienta_sugerida' (nombre de la función) "
        "y 'confianza_clasificacion' (float entre 0.0 y 1.0)."
    ),
    "response_schema": {
        "type": "OBJECT",
        "properties": {
            "intent": {"type": "STRING", "enum": ["BUSQUEDA_RAG_NORMATIVA", "GENERAR_REPORTE", "CONVERSACIONAL"]},
            "herramienta_sugerida": {"type": "STRING"},
            "confianza_clasificacion": {"type": "NUMBER"},
        },
        "required": ["intent", "herramienta_sugerida", "confianza_clasificacion"],
    },
}
