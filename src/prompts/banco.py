BANCO_DE_PROMPTS = [
    {
        "nombre": "evaluar_orientacion_ciudadana",
        "system_instruction": (
            "Eres un asistente de orientación pública en Chile. Evalúa la consulta del ciudadano sobre "
            "beneficios de salud (Fonasa) o sociales (RSH). Responde únicamente con un JSON que contenga: "
            "'respuesta_directa' (síntesis de la orientación), 'requiere_tramite_presencial' (boolean), "
            "'nivel_urgencia' ('Bajo', 'Medio' o 'Alto') y 'instituciones_involucradas' (lista de textos)."
        ),
        "ejemplo_usuario": "¿Qué debo hacer si cambié de trabajo y quiero pasarme al Tramo B de Fonasa?",
        "claves_esperadas": [
            "respuesta_directa",
            "requiere_tramite_presencial",
            "nivel_urgencia",
            "instituciones_involucradas",
        ],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "respuesta_directa": {"type": "STRING"},
                "requiere_tramite_presencial": {"type": "BOOLEAN"},
                "nivel_urgencia": {"type": "STRING"},
                "instituciones_involucradas": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                },
            },
            "required": [
                "respuesta_directa",
                "requiere_tramite_presencial",
                "nivel_urgencia",
                "instituciones_involucradas",
            ],
        },
    },
    {
        "nombre": "extraer_datos_ciudadano",
        "system_instruction": (
            "Analiza el texto ingresado por el usuario y extrae los datos socioeconómicos mencionados. "
            "Responde únicamente con un JSON con las claves 'rut' (string o null si no hay), "
            "'tramo_fonasa' ('A', 'B', 'C', 'D' o null), 'porcentaje_rsh' (número entero entre 0 y 100 o null) "
            "y 'menciones_tramites' (lista de temas como 'Fonasa', 'RSH', 'ChileAtiende', etc.)."
        ),
        "ejemplo_usuario": "Hola, mi RUT es 18.452.119-3, actualmente estoy en el 40% del RSH y necesito saber sobre Fonasa Tramo B.",
        "claves_esperadas": [
            "rut",
            "tramo_fonasa",
            "porcentaje_rsh",
            "menciones_tramites",
        ],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "rut": {"type": "STRING", "nullable": True},
                "tramo_fonasa": {"type": "STRING", "nullable": True},
                "porcentaje_rsh": {"type": "INTEGER", "nullable": True},
                "menciones_tramites": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                },
            },
            "required": [
                "rut",
                "tramo_fonasa",
                "porcentaje_rsh",
                "menciones_tramites",
            ],
        },
    },
    {
        "nombre": "enrutador_agente_intentos",
        "system_instruction": (
            "Analiza la consulta del usuario para determinar la herramienta (tool) adecuada en el sistema. "
            "Responde únicamente con un JSON con las claves: 'intent' ('CONSULTA_PERFIL', 'BUSQUEDA_RAG_NORMATIVA', "
            "'GENERAR_REPORTE' o 'CONVERSACIONAL'), 'herramienta_sugerida' (nombre de la función en LangChain) "
            "y 'confianza_clasificacion' (float entre 0.0 y 1.0)."
        ),
        "ejemplo_usuario": "¿Cuáles son los requisitos legales para acreditar una carga familiar en Fonasa?",
        "claves_esperadas": [
            "intent",
            "herramienta_sugerida",
            "confianza_clasificacion",
        ],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "intent": {"type": "STRING"},
                "herramienta_sugerida": {"type": "STRING"},
                "confianza_clasificacion": {"type": "NUMBER"},
            },
            "required": [
                "intent",
                "herramienta_sugerida",
                "confianza_clasificacion",
            ],
        },
    },
]