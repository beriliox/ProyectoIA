from pipeline_limpieza import *

referencia = "El cielo es azul."

respuesta = "el cielo es azul"

tokens_referencia = procesar_texto(referencia)

tokens_respuesta = procesar_texto(respuesta)

comunes = set(tokens_referencia) & set(tokens_respuesta)

if tokens_referencia:
    proporcion = len(comunes) / len(set(tokens_referencia))
else:
    proporcion = 0.0

print(f"Coincidencia: {proporcion:.0%}")