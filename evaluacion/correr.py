"""Corre los casos de evaluacion/casos.json contra orientar() y guarda las métricas.

Uso: python -m evaluacion.correr
Cada caso gasta 1 petición de la cuota diaria (20 en el nivel gratuito).
"""
import json
from pathlib import Path

from app.evaluacion import calcular_metricas, resumir_metricas
from app.orientador import orientar

CARPETA = Path(__file__).parent

casos = json.loads((CARPETA / "casos.json").read_text(encoding="utf-8"))
pendientes = [c["consulta"] for c in casos if c["referencia"].startswith("TODO")]
if pendientes:
    raise SystemExit(f"Faltan referencias oficiales en casos.json para: {pendientes}")

resultados = []
for caso in casos:
    respuesta = orientar(caso["consulta"])["respuesta_directa"]
    resultados.append({"consulta": caso["consulta"], "respuesta": respuesta, **calcular_metricas(caso["referencia"], respuesta)})

resultados.sort(key=lambda r: r["f1"])  # peores primero
(CARPETA / "resultados.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
print(resumir_metricas(resultados))
