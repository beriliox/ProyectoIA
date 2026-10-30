"""Capa de integración con Gemini: petición, errores, reintentos y costo."""
import os
import json
import re
import time
import random
from typing import Callable, Any

import requests
from dotenv import load_dotenv

load_dotenv()

MODELO = "gemini-3.5-flash-lite"  # elegido en docs/decision-arquitectura.md
URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
API_KEY = os.getenv("API_KEY")

ESPERA_MAXIMA = 30  # si el proveedor pide esperar más que esto, no vale la pena reintentar
COSTO_POR_1000_TOKENS = 0.002  # referencial
costo_total_sesion = 0.0


def armar_peticion(pregunta: str, system_instruction: str = "", response_schema: dict | None = None) -> tuple[str, dict]:
    if not pregunta or not pregunta.strip():
        raise ValueError("La pregunta no puede estar vacía")
    url = f"{URL_BASE}{MODELO}:generateContent?key={API_KEY}"
    body = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": pregunta}]}],
    }
    if response_schema is not None:
        body["generationConfig"] = {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        }
    return url, body


def segundos_de_espera(respuesta) -> float | None:
    """Lee cuánto pide esperar el proveedor: header Retry-After o retryDelay de Gemini ("7900s")."""
    if respuesta.headers.get("Retry-After"):
        return float(respuesta.headers["Retry-After"])
    try:
        for detalle in respuesta.json()["error"]["details"]:
            if "retryDelay" in detalle:
                return float(detalle["retryDelay"].rstrip("s"))
    except (ValueError, KeyError, TypeError):
        pass
    return None


def enviar_peticion(url: str, body: dict) -> dict:
    try:
        respuesta = requests.post(url, json=body, timeout=30)
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Error de conexión. Verifica tu conexión a Internet.")
    except requests.exceptions.Timeout:
        raise RuntimeError("La solicitud excedió el tiempo de espera. Intenta más tarde.")

    if respuesta.status_code in (401, 403):
        raise ValueError("Credencial inválida o sin permiso. Revisa API_KEY en tu .env")
    if respuesta.status_code == 429:
        segundos = segundos_de_espera(respuesta)
        if segundos and segundos > ESPERA_MAXIMA:
            # cuota diaria agotada: reintentar solo gasta más cuota
            raise RuntimeError(f"Cuota agotada. El proveedor pide esperar {segundos:.0f}s.")
        raise TimeoutError("Límite de uso excedido.")
    if respuesta.status_code >= 500:
        raise TimeoutError("El proveedor no pudo procesar la petición.")
    if respuesta.status_code != 200:
        raise RuntimeError(f"Error en la solicitud: {respuesta.status_code}")

    try:
        return respuesta.json()
    except requests.exceptions.JSONDecodeError:
        raise RuntimeError("La respuesta del proveedor no es JSON válido.")


def extraer_texto(datos: dict) -> str:
    try:
        return datos["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError("La respuesta no tiene la estructura esperada.")


def parsear_respuesta_json(texto: str, claves_requeridas: list[str] | None = None) -> dict:
    texto_limpio = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip())
    try:
        datos = json.loads(texto_limpio)
    except json.JSONDecodeError:
        raise ValueError("La respuesta del modelo no es JSON válido")
    faltantes = [clave for clave in claves_requeridas or [] if clave not in datos]
    if faltantes:
        raise ValueError(f"A la respuesta le faltan claves: {faltantes}")
    return datos


def con_reintento(funcion: Callable[[], Any], intentos: int = 3, espera_base: float = 2, espera_maxima: float = ESPERA_MAXIMA) -> Any:
    for intento in range(1, intentos + 1):
        try:
            return funcion()
        except TimeoutError:
            if intento == intentos:
                raise
            espera = min(espera_base * (2 ** (intento - 1)), espera_maxima)
            espera += random.uniform(0, espera * 0.1)
            print(f"Intento {intento} de {intentos} falló. Reintentando en {espera:.1f}s...")
            time.sleep(espera)


def registrar_costo(respuesta: dict) -> float:
    global costo_total_sesion
    total_tokens = respuesta.get("usageMetadata", {}).get("totalTokenCount", 0)
    costo = (total_tokens / 1000) * COSTO_POR_1000_TOKENS
    costo_total_sesion += costo
    print(f"Operación: {total_tokens} tokens, costo: ${costo:.5f} (acumulado: ${costo_total_sesion:.5f})")
    return costo


def consultar_modelo(pregunta: str, system_instruction: str = "", response_schema: dict | None = None) -> str:
    url, body = armar_peticion(pregunta, system_instruction, response_schema)
    try:
        respuesta = con_reintento(lambda: enviar_peticion(url, body))
    except TimeoutError:
        raise RuntimeError("El servicio no respondió tras varios intentos. Intenta más tarde.")
    registrar_costo(respuesta)
    return extraer_texto(respuesta)
