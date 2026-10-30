"""Pipeline de texto: normalizar y tokenizar."""
import re


def limpiar_texto(texto: str) -> str:
    """Minúsculas, sin puntuación y con espacios simples."""
    if not isinstance(texto, str):
        raise TypeError(f"limpiar_texto espera str, no {type(texto).__name__}")
    texto = re.sub(r"[^\w\s]", "", texto.lower())
    return re.sub(r"\s+", " ", texto).strip()


def tokenizar(texto_limpio: str) -> list[str]:
    return texto_limpio.split()


def procesar_texto(texto: str) -> list[str]:
    return tokenizar(limpiar_texto(texto))
