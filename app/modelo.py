"""Capa 1, integración con el modelo: el único lugar que crea el cliente de Gemini.

Base en los ejemplos: ejemplos/consumir_gemini.py y ejemplos/cliente.py (reintentos)
y ejemplos/cadena_tres_pasos.py (ChatGoogleGenerativeAI).
"""
import os

from dotenv import load_dotenv

load_dotenv()

MODELO = "gemini-3.1-flash-lite"
TIMEOUT_SEGUNDOS = 20  # bloque 20: una demora se vuelve excepción y la atrapan los fallbacks
REINTENTOS = 2  # reemplaza a con_reintento del cliente REST


def crear_modelo(temperatura: float = 0):
    from langchain_google_genai import ChatGoogleGenerativeAI  # import tardío: las pruebas usan modelos falsos

    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("Falta API_KEY en el archivo .env")
    return ChatGoogleGenerativeAI(
        model=MODELO,
        api_key=api_key,
        temperature=temperatura,
        timeout=TIMEOUT_SEGUNDOS,
        max_retries=REINTENTOS,
    )
