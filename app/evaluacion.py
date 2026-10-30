"""Métricas de calidad: precisión, cobertura y F1 por tokens. Funciones puras, sin llamadas al modelo."""
from collections import Counter

from app.procesamiento import procesar_texto


def contar_coincidencias(tokens_referencia: list[str], tokens_respuesta: list[str]) -> int:
    return sum((Counter(tokens_referencia) & Counter(tokens_respuesta)).values())


def calcular_metricas(texto_referencia: str, texto_respuesta: str) -> dict[str, float]:
    tokens_referencia = procesar_texto(texto_referencia)
    tokens_respuesta = procesar_texto(texto_respuesta)
    if not tokens_referencia or not tokens_respuesta:
        return {"precision": 0.0, "cobertura": 0.0, "f1": 0.0}

    coincidencias = contar_coincidencias(tokens_referencia, tokens_respuesta)
    precision = coincidencias / len(tokens_respuesta)
    cobertura = coincidencias / len(tokens_referencia)
    f1 = 2 * precision * cobertura / (precision + cobertura) if coincidencias else 0.0
    return {"precision": precision, "cobertura": cobertura, "f1": f1}


def resumir_metricas(resultados: list[dict]) -> dict[str, float]:
    n = len(resultados) or 1
    return {
        f"{metrica}_promedio": sum(r[metrica] for r in resultados) / n
        for metrica in ("precision", "cobertura", "f1")
    }
