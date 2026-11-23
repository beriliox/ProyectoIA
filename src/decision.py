def estimar_costo_de_etiquetar(num_ejemplos, minutos_por_ejemplo, costo_por_hora):
    horas = (num_ejemplos * minutos_por_ejemplo) / 60
    costo = horas * costo_por_hora
    return horas, costo

def recomendar_estrategia(respuestas):
    puntos = {"RAG": 0, "Fine-tuning completo": 0, "PEFT": 0}

    if respuestas["informacion_cambia_seguido"]:
        puntos["RAG"] += 3
    if respuestas["problema_de_formato_o_tono"]:
        puntos["PEFT"] += 2
        puntos["Fine-tuning completo"] += 1
    if respuestas["dataset_grande_y_de_calidad"]:
        puntos["Fine-tuning completo"] += 2
        puntos["PEFT"] += 1
    if respuestas["presupuesto_limitado_o_iterar_rapido"]:
        puntos["RAG"] += 2
        puntos["PEFT"] += 1
    if respuestas["necesita_multiples_variantes"]:
        puntos["PEFT"] += 2

    maximo = max(puntos.values())
    ganadoras = [tecnica for tecnica, p in puntos.items() if p == maximo]
    return puntos, ganadoras

def generar_esqueleto_decision(problema, puntos, ganadoras):
    empate = len(ganadoras) > 1
    lineas = []
    lineas.append("# Decision de personalizacion")
    lineas.append("")
    lineas.append("## 1. El problema")
    lineas.append(problema)
    lineas.append("")
    lineas.append("## 2. Resultado del metodo de decision")
    for tecnica, p in sorted(puntos.items(), key=lambda x: -x[1]):
        lineas.append(f"- {tecnica}: {p} puntos")
    if empate:
        lineas.append("")
        lineas.append(f"**Empate entre: {', '.join(ganadoras)}**")
    lineas.append("")
    lineas.append("## 3. Tecnica elegida y por que")
    if empate:
        lineas.append(
            "[COMPLETAR: el puntaje no resolvio el empate solo -- "
            "justifica aqui con criterio propio]"
        )
    else:
        lineas.append(f"[COMPLETAR: por que {ganadoras[0]} responde mejor a este caso]")
    lineas.append("")
    lineas.append("## 4. Que necesitarias para ejecutarla")
    lineas.append(
        "[COMPLETAR: corpus faltante, o cantidad de ejemplos etiquetados que faltan]"
    )
    return "\n".join(lineas)

if __name__ == "__main__":
    #costo de etiquetar el dataset de dataset_tuning.py (14 ejemplos), a 5 minutos por ejemplo.
    #costo_por_hora = 25 es el valor de ejemplo del curso, no una tarifa real: es un supuesto
    horas, costo = estimar_costo_de_etiquetar(14, 5, 25)
    print(f"dataset actual (14 ejemplos): {horas:.2f} horas, aprox ${costo:.2f}")

    # lo que falta para llegar a 10 ejemplos por tramite (6 tramites = 60 ejemplos)
    horas_faltan, costo_faltan = estimar_costo_de_etiquetar(60 - 14, 5, 25)
    print(f"faltan 46 ejemplos para 60: {horas_faltan:.2f} horas, aprox ${costo_faltan:.2f}")

    # el mismo calculo, para un dataset de produccion de 200 ejemplos
    horas2, costo2 = estimar_costo_de_etiquetar(200, 5, 25)
    print(f"dataset de produccion (200 ejemplos): {horas2:.2f} horas, aprox ${costo2:.2f}")
    print(f"factor de crecimiento en horas: {horas2 / horas:.1f}x")

    #responder con evidencia (el número que sustenta cada respuesta va en el comentario)
    respuestas_mi_caso = {
        "informacion_cambia_seguido": False,
        "problema_de_formato_o_tono": False,
        "dataset_grande_y_de_calidad": False,
        "presupuesto_limitado_o_iterar_rapido": True,
        "necesita_multiples_variantes": False,
    }

    if any(valor is None for valor in respuestas_mi_caso.values()):
        raise SystemExit("Completa las cinco respuestas con True o False antes de continuar.")

    puntos, ganadoras = recomendar_estrategia(respuestas_mi_caso)
    print()
    print(puntos)
    print("candidatas:", ganadoras)

    print()
    for clave in respuestas_mi_caso:
        variante = dict(respuestas_mi_caso)
        variante[clave] = not variante[clave]
        puntos_v, ganadoras_v = recomendar_estrategia(variante)
        cambio = "CAMBIA" if set(ganadoras_v) != set(ganadoras) else "igual"
        print(f"{clave} -> {not respuestas_mi_caso[clave]}: {ganadoras_v}  [{cambio}]")

    #generar el esqueleto.
    esqueleto = generar_esqueleto_decision(
        "El asistente debe clasificar cada mensaje en un trámite fijo y responder siempre el mismo JSON.",
        puntos,
        ganadoras,
    )
    print()
    print(esqueleto)

    with open("docs/decision_personalizacion.md", "w", encoding="utf-8") as f:
        f.write(esqueleto)
