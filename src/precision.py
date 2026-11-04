from collections import Counter
from pipeline_limpieza import *
from cliente import *
import json


def contar_coincidencias(
    tokens_referencia: list[str],
    tokens_respuesta: list[str],
) -> int:
    """Cuenta las coincidencias entre referencia y respuesta."""
    conteo_referencia = Counter(tokens_referencia)
    conteo_respuesta = Counter(tokens_respuesta)
    interseccion = conteo_referencia & conteo_respuesta
    return sum(interseccion.values())

def calcular_precision_cobertura_f1(
    tokens_referencia: list[str],
    tokens_respuesta: list[str],
) -> dict[str, float]:
    """Calcula precisión, cobertura y F1 de dos listas de tokens."""
    coincidencias = contar_coincidencias(
        tokens_referencia, tokens_respuesta
    )

    if not tokens_respuesta or not tokens_referencia:
        return {"precision": 0.0, "cobertura": 0.0, "f1": 0.0}

    precision = coincidencias / len(tokens_respuesta)
    cobertura = coincidencias / len(tokens_referencia)

    if precision + cobertura == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * cobertura / (precision + cobertura)

    resultado = {
        "precision": precision,
        "cobertura": cobertura,
        "f1": f1,
    }

    return resultado

def calcular_metricas(texto_referencia, texto_respuesta):
    tokens_referencia = procesar_texto(texto_referencia)
    tokens_respuesta = procesar_texto(texto_respuesta)
    
    return calcular_precision_cobertura_f1(
        tokens_referencia, tokens_respuesta
    )

casos = [
    (
        "¿Quiénes pueden ser beneficiarios de Fonasa?",
        "Fonasa incorpora a todas las personas que viven en Chile, sin importar edad, ingresos, enfermedades preexistentes ni nacionalidad.",
    ),
    (
        "¿Cuánto se paga por las cargas familiares en Fonasa?",
        "Las cargas familiares no pagan extra; con el 7% de cotización están cubiertas.",
    ),
    (
        "¿Qué porcentaje del sueldo se cotiza en Fonasa?",
        "Se cotiza el 7% del ingreso imponible.",
    ),
    (
        "¿Qué es el Copago Cero de Fonasa?",
        "Desde septiembre de 2022 las atenciones en la red pública, Modalidad de Atención Institucional, no tienen copago para ningún tramo.",
    ),
    (
        "¿Cuántos tramos tiene Fonasa?",
        "Fonasa tiene cuatro tramos, A, B, C y D, según el nivel de ingresos y la vulnerabilidad económica.",
    ),
    (
        "¿Quiénes pertenecen al tramo A de Fonasa?",
        "Las personas carentes de recursos y los causantes de subsidio familiar.",
    ),
    (
        "¿Quiénes pertenecen al tramo B de Fonasa?",
        "Las personas con un ingreso imponible mensual menor o igual a $553.553.",
    ),
    (
        "¿Quiénes pertenecen al tramo C de Fonasa?",
        "Las personas con un ingreso imponible mensual desde $553.554 y menor o igual a $808.187.",
    ),
    (
        "¿Quiénes pertenecen al tramo D de Fonasa?",
        "Las personas con un ingreso imponible mensual mayor a $808.188.",
    ),
    (
        "¿Qué pasa si estoy en el tramo D de Fonasa y tengo tres cargas familiares?",
        "Con tres o más cargas familiares, una persona del tramo D pasa al tramo C.",
    ),
    (
        "¿Puede una persona del tramo A comprar bonos de libre elección?",
        "No, el tramo A solo puede atenderse en la red pública, en la Modalidad de Atención Institucional.",
    ),
    (
        "¿Qué tramos de Fonasa pueden comprar bonos en la Modalidad de Libre Elección?",
        "Los tramos B, C y D pueden comprar bonos en prestadores privados en convenio con Fonasa.",
    ),
    (
        "¿De qué depende el valor de un bono de Fonasa en libre elección?",
        "El valor del bono depende del médico o centro médico donde te atiendas, no del tramo.",
    ),
    (
        "¿Qué es el Registro Social de Hogares?",
        "Es un sistema de información que caracteriza socioeconómicamente a la población para apoyar la selección de beneficiarios de programas sociales.",
    ),
    (
        "¿Qué necesito para ingresar al Registro Social de Hogares?",
        "Se requiere cédula de identidad vigente y se solicita con ClaveÚnica en línea, en el municipio o en ChileAtiende.",
    ),
    (
        "¿Qué considera el Registro Social de Hogares para calcular la calificación socioeconómica?",
        "Considera los ingresos de los últimos 12 meses, el número y características de los integrantes y los bienes o servicios de alto valor.",
    ),
    (
        "¿Qué se considera un hogar en el Registro Social de Hogares?",
        "Un grupo de personas que residen en una misma vivienda y comparten un presupuesto de alimentación.",
    ),
    (
        "¿Qué es la Cartola Hogar?",
        "Es un documento que muestra la información de tu hogar en el Registro Social de Hogares, usada para calcular la calificación socioeconómica.",
    ),
    (
        "¿Cómo descargo mi Cartola Hogar?",
        "Ingresa a Ventanilla Única Social con tu ClaveÚnica y presiona Descargar mi Cartola Hogar.",
    ),
    (
        "¿Cómo corrijo un dato incorrecto del Estado en mi Registro Social de Hogares?",
        "Con una rectificación, que se hace solo de forma presencial en la oficina del Registro Social de Hogares de tu municipalidad.",
    ),
]

resultados = []

for consulta, referencia in casos:
    respuesta = consultar_modelo(consulta, system_instruction="Eres un orientador sobre Fonasa y el Registro Social de Hogares de Chile. Responde en español en una sola oración de máximo 25 palabras. Sin listas, ejemplos ni introducciones.")
    
    metricas = calcular_metricas(referencia, respuesta)
    
    print("Consulta:", consulta)
    print("Referencia:", referencia)
    print("Respuesta:", respuesta)
    print("Métricas:", metricas)
    
    resultados.append({
        "id": len(resultados) + 1,
        "consulta": consulta,
        "referencia": referencia,
        "respuesta": respuesta,
        **metricas,
    })

resultados = sorted(resultados, key=lambda r: r["f1"])

with open(
    "docs/resultados_metricas.json", "w", encoding="utf-8"
) as archivo:
    json.dump(resultados, archivo, indent=2, ensure_ascii=False)

def resumir_metricas(resultados):
    if not resultados:
        return {
            "precision_promedio": 0,
            "cobertura_promedio": 0,
            "f1_promedio": 0,
        }
    n = len(resultados)
    return {
        "precision_promedio": sum(
            r["precision"] for r in resultados
        ) / n,
        "cobertura_promedio": sum(
            r["cobertura"] for r in resultados
        ) / n,
        "f1_promedio": sum(r["f1"] for r in resultados) / n,
    }
    
print("Promedios")
print(resumir_metricas(resultados))
    
peores_casos = sorted(resultados, key=lambda r: r["f1"])

muestra_para_revisar = peores_casos[:5] + peores_casos[-5:]

for caso in muestra_para_revisar:

    print(caso["consulta"], caso["f1"])
    
    
# referencia = procesar_texto(
#     "Python es un lenguaje de programación interpretado."
# )

# texto_respuesta = consultar_modelo("¿Qué es Python?",
#                                    system_instruction="Responde en español con una definición breve, en una sola oración de máximo 15 palabras. Sin listas, ejemplos ni introducciones.")

# respuesta = procesar_texto(texto_respuesta)
# resultado = calcular_precision_cobertura_f1(referencia, respuesta)

# print("Respuesta:", texto_respuesta)
# print("Tokens de referencia:", len(referencia))
# print("Tokens de respuesta:", len(respuesta))
# print(resultado)