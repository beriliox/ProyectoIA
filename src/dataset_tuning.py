import json
from collections import Counter
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

"""
Dataset de tuning (PEFT) para el asistente de trámites: clasificar cada mensaje del usuario
en un trámite fijo y devolver SIEMPRE el mismo JSON {"tramite": ..., "accion": ...}.
Es comportamiento consistente (formato), no conocimiento: la información la sigue dando el RAG.
No llama a la API: solo revisa el SDK, construye y valida.
"""

#Paso 0: Revisar que el SDK expone lo necesario para el tuning (igual que tuning_opciones.py)
def revisar_sdk():
    try:
        print("Modos de tuning disponibles:")
        for modo in types.TuningMode:
            print(" ", modo)
            #TUNING_MODE_FULL: reentrena todos los parámetros del modelo
            #TUNING_MODE_PEFT_ADAPTER: congela el modelo y entrena solo un adapter pequeño (el que usaría este dataset)

        print()
        print("Tamaños de adapter disponibles (solo aplica a PEFT):")
        for tamanio in types.AdapterSize:
            print(" ", tamanio)
    except AttributeError as e:
        raise SystemExit(f"Tu versión del SDK no expone este tipo: {e}. Actualiza con: pip install -U google-genai")

    print()
    for campo in ["epoch_count", "learning_rate_multiplier", "batch_size"]:
        try:
            descripcion = types.CreateTuningJobConfig.model_fields[campo].description
            print(campo, "->", descripcion)
        except KeyError:
            print(campo, "-> este campo no existe en tu versión del SDK")

#Paso 1: Construcción del dataset (sin RUT ni datos personales, sin montos ni tramos en los output)
ejemplos_raw = [
    ("Quiero actualizar mi tramo de Fonasa, ¿cómo lo hago?", #text_input
     {"tramite": "fonasa", "accion": "orientar canales de Fonasa"}), #output
    ("Me cambié de trabajo y creo que mi tramo de Fonasa ya no corresponde.",
     {"tramite": "fonasa", "accion": "orientar canales de Fonasa"}),
    ("¿Dónde actualizo los datos de mi hogar en el registro social?",
     {"tramite": "registro_social", "accion": "orientar canales del Registro Social"}),
    ("Necesito poner al día mi Registro Social de Hogares, ¿puedo hacerlo en la municipalidad?",
     {"tramite": "registro_social", "accion": "orientar canales del Registro Social"}),
    ("Somos cuatro en la casa, ¿cuánto nos toca por persona?",
     {"tramite": "ingreso", "accion": "pedir ingreso total y cantidad de integrantes"}),
    ("En mi hogar entran 900 mil al mes y vivimos tres, calcula el ingreso por integrante.",
     {"tramite": "ingreso", "accion": "calcular ingreso por integrante"}),
    ("Anota que nos cambiamos de domicilio el mes pasado.",
     {"tramite": "nota", "accion": "guardar nota del tema domicilio"}),
    ("Me equivoqué en la nota de integrantes, ahora somos cinco.",
     {"tramite": "nota", "accion": "reemplazar nota del tema integrantes"}),
    ("Guarda mi RUT en una nota para no olvidarlo.",
     {"tramite": "nota", "accion": "rechazar: la nota no puede contener RUT ni datos personales"}),
    ("Quiero pedir que actualicen mi registro social porque nació mi hija.",
     {"tramite": "solicitud", "accion": "pedir aprobación humana para el motivo integrantes"}),
    ("Envía una solicitud de actualización porque bajaron los ingresos de la casa.",
     {"tramite": "solicitud", "accion": "pedir aprobación humana para el motivo ingresos"}),
    ("¿Cuánto es el monto del bono de invierno?",
     {"tramite": "fuera_de_alcance", "accion": "indicar que solo orienta sobre Fonasa y Registro Social"}),
    ("¿Me ayudas a sacar la licencia de conducir?",
     {"tramite": "fuera_de_alcance", "accion": "indicar que solo orienta sobre Fonasa y Registro Social"}),
    ("¿En qué tramo de Fonasa voy a quedar con lo que gano?",
     {"tramite": "fuera_de_alcance", "accion": "indicar que no asigna tramos y orientar canales de Fonasa"}),
]

#Lista de TuningExample: text_input = mensaje, output = JSON como texto
examples = [
    types.TuningExample(text_input=texto, output=json.dumps(salida, ensure_ascii=False))
    for texto, salida in ejemplos_raw
]

#Paso 2: Balance por categoría
def chequear_balance(ejemplos_raw: list[tuple[str, dict]], clave: str) -> Counter:
    categorias = Counter(salida[clave] for _, salida in ejemplos_raw)
    return categorias

#Paso 3: Validación (mismo cuerpo que laboratorio_dataset.py)
def validar_dataset(examples: list[types.TuningExample], claves_esperadas: tuple[str, ...]) -> list[str]:
    problemas = []
    vistos = set()
    for i, ej in enumerate(examples):
        if not ej.text_input or not ej.text_input.strip():
            problemas.append(f"ejemplo {i}: text_input vacio")
        if not ej.output or not ej.output.strip():
            problemas.append(f"ejemplo {i}: output vacio")
            continue
        if ej.text_input in vistos:
            problemas.append(f"ejemplo {i}: text_input duplicado")
        vistos.add(ej.text_input)
        try:
            salida = json.loads(ej.output)
        except json.JSONDecodeError:
            problemas.append(f"ejemplo {i}: output no es JSON valido")
            continue
        for clave in claves_esperadas:
            if clave not in salida:
                problemas.append(f'ejemplo {i}: output no tiene la clave "{clave}"')
    return problemas

if __name__ == "__main__":
    CLAVES = ("tramite", "accion")

    revisar_sdk()

    #Prueba 1: balance
    print("\n-- BALANCE --")
    for categoria, cuenta in chequear_balance(ejemplos_raw, "tramite").most_common():
        print(f"{categoria}: {cuenta}")

    #Prueba 2: validación del dataset real
    problemas = validar_dataset(examples, claves_esperadas=CLAVES)
    print(f"\n{len(examples)} ejemplos, {len(problemas)} problemas encontrados")
    for p in problemas:
        print(p)

    #Prueba 3: romper ejemplos a propósito y confirmar que el validador los detecta
    rotos = examples + [
        types.TuningExample(text_input=examples[0].text_input, output=examples[0].output), #duplicado
        types.TuningExample(text_input="¿Dónde actualizo Fonasa?", output='{"tramite": "fonasa"}'), #falta accion
        types.TuningExample(text_input="Hola", output="{'tramite': 'fuera_de_alcance'}"), #comillas simples
    ]
    print("\n-- DATASET ROTO A PROPÓSITO --")
    for p in validar_dataset(rotos, claves_esperadas=CLAVES):
        print(p)

    #Dataset y configuración listos para el paso 4 (opcional). NO se envía: client.tunings.tune puede generar costo
    dataset = types.TuningDataset(examples=examples)
    config = types.CreateTuningJobConfig(
        tuned_model_display_name="asistente-tramites-clasificador",
        epoch_count=5
    )
    print(f"\nDataset listo: {len(dataset.examples)} ejemplos. Config: {config.tuned_model_display_name}, epochs={config.epoch_count}")
