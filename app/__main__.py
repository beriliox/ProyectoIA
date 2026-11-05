"""Uso: python -m app "¿Cómo cambio de tramo en Fonasa?" """
import json
import logging
import sys

from app.peticiones import atender

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

if len(sys.argv) < 2 or not " ".join(sys.argv[1:]).strip():
    sys.exit('Uso: python -m app "tu consulta"')

print(json.dumps(atender(" ".join(sys.argv[1:])), indent=2, ensure_ascii=False))
