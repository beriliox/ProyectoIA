import time
from typing import Callable, Any

from src.consumir_gemini import armar_peticion, enviar_peticion, extraer_texto

MODELO = "gemini-3.5-flash"

#def con_reintento(): #funcion, intentos
  #iterar cantidad de intentos
    #intentar ejecutar la funcion
    #TimeoutError:
      #raise

      #Espera
      #time.sleep(esperar_segundos)
  
def con_reintento(funcion: Callable[..., Any], intentos: int = 3, esperar_segundos: int = 2) -> Any:
	for intento in range(intentos):
		try:
			return funcion()
		except TimeoutError:
			if intento == intentos - 1:
				raise
			print(f"Intento {intento + 1} de {intentos} falló por límite de uso/servidor. Reintentando...")
			time.sleep(esperar_segundos)

def consultar_modelo(
	pregunta: str,
	system_instruction: str = "",
) -> str:
	url, body = armar_peticion(MODELO, pregunta, system_instruction)
	try:
			respuesta = con_reintento(lambda: enviar_peticion(url, body))
	except TimeoutError:
			raise RuntimeError("El servicio no respondió tras varios intentos. Intenta más tarde.")
	return extraer_texto(respuesta)
 
#Cómo ejecuto esto?
if __name__ == "__main__":
	try:
		respuesta = consultar_modelo("¿Cuál es la capital de Chile?")
		print(respuesta)
	except ValueError as error:
		print(f"Error de configuración: {error}")
	except RuntimeError as error:
		print(f"El servicio no respondió tras varios intentos: {error}")