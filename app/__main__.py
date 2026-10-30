"""Uso: python -m app "¿Cómo cambio de tramo en Fonasa?" """
import json
import sys

from app.orientador import orientar

if len(sys.argv) < 2:
    sys.exit('Uso: python -m app "tu consulta"')

try:
    print(json.dumps(orientar(" ".join(sys.argv[1:])), indent=2, ensure_ascii=False))
except (ValueError, RuntimeError) as error:
    sys.exit(f"No se pudo completar la consulta: {error}")
