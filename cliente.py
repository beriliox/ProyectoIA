import time
from typing import Callable, Any

from src.consumir_gemini import armar_peticion, enviar_peticion, extraer_texto

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
        print(f"Intento {intento + 1} de {intentos} fallópor límite de uso/servidor. Reintentando...")
        time.sleep(esperar_segundos)

#Cómo ejecuto esto?
if __name__ == "__main__":
    url, cuerpo = armar_peticion("gemini-3.5-flash-lite", "Hola", "")
    respuesta = con_reintento(lambda: enviar_peticion(url, cuerpo))
    print(respuesta)