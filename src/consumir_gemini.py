import os
import requests
from dotenv import load_dotenv

import time

load_dotenv()

# CONSTANTES
MODELO = "gemini-3.6-flash"
URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
API_KEY = os.getenv("API_KEY")

#función para crear la solicitud
def armar_peticion(modelo, pregunta, system_instruction): #pregunta = "Confirma la conexion"
    if not pregunta:
      raise ValueError("La pregunta no puede estar vacía")
    url = f"{URL_BASE}{modelo}:generateContent?key={API_KEY}" #url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=MI API KEY"
    body = {
        "systemInstruction": {
          "parts": [ {"text": system_instruction} ]
        },
        "contents": 
            [{"parts": [{"text": pregunta}]}]
        }
    return url, body

#función envía la petición
def enviar_peticion(url, body):
  try:
    respuesta = requests.post(url, json=body, timeout=30)
  except requests.exceptions.ConnectionError:
    raise RuntimeError("Error de conexión. Por favor, verifica tu conexión a Internet.")
  except requests.exceptions.Timeout:
    raise RuntimeError("La solicitud ha excedido el tiempo de espera. Intenta nuevamente más tarde.")

  if respuesta.status_code != 200:
    raise RuntimeError(f"Error en la solicitud: {respuesta.status_code}")

  try:
    return respuesta.json()
  except requests.exceptions.JSONDecodeError:
    raise RuntimeError("Error al decodificar la respuesta JSON. La respuesta recibida no es válida.")

def extraer_texto(datos): #Gemini
  try:
    return datos["candidates"][0]["content"]["parts"][0]["text"]
  except (KeyError, IndexError):
    raise RuntimeError("Error al extraer el texto de la respuesta. La estructura de datos recibida no es la esperada.")

def obtener_dato_de_prueba(pregunta): #pregunta = "Confirma la conexion"
    system_instruction = "Eres un asistente amigable y respondes en máximo 2 palabras."
    url, body = armar_peticion("gemini-3.6-flash", pregunta, system_instruction) #obtiene url y body
    inicio = time.perf_counter() #Empezar el contador
    #url = resultado de armar_peticion
    #body = resultado de armar_peticion
    datos = enviar_peticion(url, body)

    fin = time.perf_counter() #Termina el contador
    latencia = fin - inicio
    print(f"Latencia: {latencia:.2f} segundos")

    costo = calcular_costo(datos, 0.00000075, 0.00000375)
    print(f"Costo de la petición: ${costo:.6f} USD")
    return extraer_texto(datos)

# def calcular_costo(datos: dict, precio_entrada: float, precio_salida: float) -> float:
def calcular_costo(datos, precio_entrada, precio_salida):
  # datos = {usageMetadata}
  uso = datos["usageMetadata"]

  tokens_entrada = uso["promptTokenCount"]
  tokens_salida = uso["candidatesTokenCount"]
  tokens_razonamiento = uso.get("thoughtsTokenCount", 0)
  costo = (tokens_entrada * precio_entrada) + ((tokens_salida + tokens_razonamiento) * precio_salida)
  return costo

try:
  print(obtener_dato_de_prueba("Confirma en una frase corta que esta conexión funciona"))
except (ValueError, RuntimeError) as error:
  print("No se pudo completar la operación: ", error)