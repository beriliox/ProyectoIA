# Clase 2026-10-27: límites de uso, registro de costo y pruebas unitarias

Esta guía explica los dos commits de la clase del 27 de octubre de 2026. Está escrita para alguien que recién empieza con Python: cada concepto del lenguaje se explica la primera vez que aparece.

| Commit | Mensaje | Archivos |
|---|---|---|
| `c0e5788` | feat: se agrega límites de uso y registro de costo | `cliente.py` |
| `925314b` | feat: agrega suite de pruebas unitarias del cliente modular | `test_cliente.py`, `requirements.txt` |

---

## 1. El panorama general

El proyecto le hace preguntas a Gemini (el modelo de IA de Google) a través de internet. Eso tiene dos problemas prácticos:

1. **La API a veces dice "espera".** Si haces muchas preguntas seguidas, Google responde con un error **429** (límite de uso). Si su servidor tiene problemas, responde con un error **500 o mayor**. En ambos casos lo correcto es esperar un poco y volver a intentar.
2. **Cada pregunta cuesta dinero.** Google cobra por *tokens* (pedacitos de texto, más o menos ¾ de una palabra). Conviene saber cuánto vas gastando.

El primer commit resuelve esos dos problemas en `cliente.py`. El segundo commit agrega **pruebas automáticas** que confirman que todo funciona sin gastar ni un token real.

### Cómo se conectan las piezas

```
consultar_modelo("¿Cuál es la capital de Chile?")
   │
   ├─ armar_peticion(...)      → arma la URL y el mensaje para Gemini
   │
   ├─ con_reintento(...)       → intenta enviar; si hay 429/5xx espera y reintenta
   │     └─ enviar_peticion(...)  → hace la petición HTTP real
   │
   ├─ registrar_costo(...)     → calcula y suma lo que costó
   │
   └─ extraer_texto(...)       → saca el texto de la respuesta
```

`armar_peticion`, `enviar_peticion` y `extraer_texto` viven en `src/consumir_gemini.py` y existían antes de esta clase. `con_reintento`, `registrar_costo` y `consultar_modelo` viven en `cliente.py`.

---

## 2. Conceptos de Python que vas a necesitar

### Funciones

Una función es un bloque de código con nombre que se puede reutilizar. Se define con `def`:

```python
def saludar(nombre: str) -> str:
    return f"Hola, {nombre}"
```

- `nombre` es un **parámetro**: el dato que recibe la función.
- `: str` y `-> str` son **anotaciones de tipo**: indican que `nombre` debería ser texto y que la función devuelve texto. Python no las obliga a cumplir; sirven como documentación.
- `return` devuelve el resultado y termina la función.
- `f"Hola, {nombre}"` es un **f-string**: un texto donde lo que está entre `{}` se reemplaza por su valor. `{costo:.5f}` significa "muestra `costo` con 5 decimales".

Un parámetro puede tener **valor por defecto**: `intentos: int = 3` significa "si no me dicen cuántos intentos, uso 3".

### Excepciones (errores)

Cuando algo sale mal, Python **lanza una excepción**. Si nadie la atrapa, el programa se detiene. Hay varios tipos, y el proyecto usa cada uno con un significado distinto:

| Excepción | Qué significa en este proyecto |
|---|---|
| `ValueError` | Problema de configuración (por ejemplo, la API key es inválida: error 401/403). Reintentar no sirve. |
| `TimeoutError` | Problema temporal (límite de uso 429 o servidor caído 5xx). Reintentar sí puede servir. |
| `RuntimeError` | El servicio falló definitivamente, ya después de reintentar. |

Para lanzar una excepción se usa `raise`. Para atraparla se usa `try` / `except`:

```python
try:
    hacer_algo_riesgoso()
except TimeoutError:
    print("Falló, pero lo manejé")
```

Si dentro del `try` ocurre un `TimeoutError`, Python salta al bloque `except`. Cualquier otro tipo de error **no** se atrapa y sigue su camino. Un `raise` solo, sin nada más, vuelve a lanzar la misma excepción que se acaba de atrapar.

### Diccionarios y `.get()`

Un diccionario guarda pares clave → valor:

```python
uso = {"totalTokenCount": 381}
uso["totalTokenCount"]          # 381
uso.get("totalTokenCount", 0)   # 381
uso.get("otraClave", 0)         # 0 (la clave no existe, devuelve el valor por defecto)
```

`.get(clave, por_defecto)` es la forma segura de leer: si la clave no existe, no falla.

### `lambda`

Una `lambda` es una función de una línea, sin nombre:

```python
lambda: enviar_peticion(url, body)
```

Esto **no** envía la petición. Crea una función que, *cuando alguien la llame*, enviará la petición. Así `con_reintento` puede llamarla varias veces si hace falta.

### Variables globales y `global`

Una variable definida fuera de cualquier función (como `costo_total_sesion = 0.0`) es **global**: la ve todo el archivo. Para *modificarla* desde dentro de una función hay que avisarle a Python con `global costo_total_sesion`. Sin esa línea, Python creería que quieres una variable nueva solo dentro de la función.

### `with`

`with` abre un "contexto" que se cierra solo al terminar el bloque. En las pruebas se usa para cambiar algo temporalmente y que se restaure automáticamente al salir.

---

## 3. Commit `c0e5788`: límites de uso y registro de costo

### Qué cambió

| Antes | Después |
|---|---|
| `con_reintento` esperaba siempre 2 segundos fijos. | Espera cada vez más (2 s, 4 s, 8 s…) con un poco de azar. |
| No se sabía cuánto costaba cada consulta. | Nueva función `registrar_costo` y un total acumulado. |
| `MODELO = "gemini-3.5-flash"` | `MODELO = "gemini-3.6-flash"` |
| Se agregó `import random` (para el azar de la espera). | |

### `con_reintento(funcion, intentos=3, espera_base=2, espera_maxima=30)`

**Propósito:** ejecutar una función y, si falla por un problema temporal (`TimeoutError`), esperar y volver a intentar.

**Parámetros:**

| Parámetro | Qué es |
|---|---|
| `funcion` | La función a ejecutar (aquí, la `lambda` que envía la petición). |
| `intentos` | Cuántas veces intentarlo en total. Por defecto 3. |
| `espera_base` | Segundos de la primera espera. Por defecto 2. |
| `espera_maxima` | Tope de segundos para cualquier espera. Por defecto 30. |

**Código, paso a paso:**

```python
for intento in range(1, intentos + 1):
```
Repite el bloque con `intento` valiendo 1, 2 y 3. (`range(1, 4)` produce 1, 2, 3: el último número no se incluye.)

```python
    try:
        return funcion()
```
Intenta ejecutar la función. Si funciona, devuelve el resultado y **sale** de `con_reintento` de inmediato.

```python
    except TimeoutError:
        if intento == intentos:
            raise
```
Si falló por `TimeoutError` y era el último intento, ya no hay más oportunidades: vuelve a lanzar el error para que lo maneje quien llamó.

```python
        espera = min(espera_base * (2 ** (intento - 1)), espera_maxima)
```
Calcula cuánto esperar. `**` es "elevado a". Con `espera_base = 2`:

| `intento` | Cálculo | Espera |
|---|---|---|
| 1 | 2 × 2⁰ = 2 × 1 | 2 s |
| 2 | 2 × 2¹ = 2 × 2 | 4 s |
| 3 | 2 × 2² = 2 × 4 | 8 s |

Esto se llama **backoff exponencial**: cada espera duplica la anterior, para darle más tiempo al servidor. `min(..., espera_maxima)` evita que la espera pase de 30 s.

```python
        espera_con_jitter = espera + random.uniform(0, espera * 0.1)
```
Le suma entre 0 % y 10 % extra al azar (*jitter*). Si muchos programas fallan al mismo tiempo, así no reintentan todos en el mismo segundo exacto.

```python
        print(f"Intento {intento} de {intentos} falló. Reintentando en {espera_con_jitter:.1f}s...")
        time.sleep(espera_con_jitter)
```
Avisa por pantalla y pausa el programa esos segundos.

**Importante:** solo se reintenta con `TimeoutError`. Un `ValueError` (API key inválida) sale de inmediato, porque reintentar no lo arreglaría.

### `registrar_costo(respuesta)`

**Propósito:** calcular cuánto costó una consulta y sumarlo al total de la sesión.

```python
COSTO_POR_1000_TOKENS = 0.002
costo_total_sesion = 0.0
```
Dos variables globales. Por convención, un nombre en MAYÚSCULAS indica una **constante** (un valor que no se piensa cambiar). El precio es referencial: el real depende del modelo.

```python
def registrar_costo(respuesta: dict) -> float:
    global costo_total_sesion
```
Recibe la respuesta de Gemini (un diccionario) y devuelve un número decimal (`float`). `global` permite modificar el total.

```python
    uso = respuesta.get("usageMetadata", {})
    total_tokens = uso.get("totalTokenCount", 0)
```
Gemini incluye en su respuesta una sección `usageMetadata` con cuántos tokens se usaron. Si no viniera, se usa `{}` y luego `0`, así la función nunca se cae.

```python
    costo_estimado = (total_tokens / 1000) * COSTO_POR_1000_TOKENS
    costo_total_sesion += costo_estimado
```
Calcula el costo (por ejemplo, 500 tokens → 0,5 × 0,002 = 0,001 USD) y lo suma al total. `+=` es la forma corta de `costo_total_sesion = costo_total_sesion + costo_estimado`.

```python
    print(f"Operación: {total_tokens} tokens, costo estimado: ${costo_estimado:.5f} (acumulado: ${costo_total_sesion:.5f})")
    return costo_estimado
```
Muestra el detalle y devuelve el costo de esta operación.

### `consultar_modelo(pregunta, system_instruction="")`

**Propósito:** la función "de entrada" del cliente. Quien la usa solo entrega una pregunta y recibe texto, sin preocuparse de URLs, reintentos ni costos.

```python
url, body = armar_peticion(MODELO, pregunta, system_instruction)
```
`armar_peticion` devuelve **dos** valores a la vez; Python permite guardarlos en dos variables en una línea.

```python
try:
    respuesta = con_reintento(lambda: enviar_peticion(url, body))
except TimeoutError:
    raise RuntimeError("El servicio no respondió tras varios intentos. Intenta más tarde.")
```
Envía la petición con reintentos. Si aun así se agotan los intentos, transforma el `TimeoutError` en un `RuntimeError` con un mensaje claro. Un `ValueError` no se atrapa aquí, así que sale tal cual.

```python
registrar_costo(respuesta)
return extraer_texto(respuesta)
```
Solo si la petición tuvo éxito: registra el costo y devuelve el texto. Por eso **una petición fallida nunca suma costo**.

### `if __name__ == "__main__":`

Este bloque solo corre cuando ejecutas el archivo directamente (`python cliente.py`). Si otro archivo hace `import cliente` (como las pruebas), este bloque **no** se ejecuta. Así las pruebas pueden usar las funciones sin disparar una consulta real.

---

## 4. Commit `925314b`: suite de pruebas unitarias

### ¿Qué es una prueba unitaria?

Es una función que llama a una parte de tu código con datos conocidos y **verifica** que el resultado sea el esperado. Se ejecutan todas juntas con un comando y te dicen al instante si algo se rompió.

El commit agrega:
- `test_cliente.py`, con 7 pruebas.
- `pytest` y sus dependencias en `requirements.txt` (`iniconfig`, `packaging`, `pluggy`, `Pygments`), para que cualquiera que clone el repositorio pueda correr las pruebas.

### Cómo se ejecutan

```bash
python -m pytest test_cliente.py -v
```

`-v` (verbose) muestra el nombre de cada prueba y si pasó (`PASSED`) o falló (`FAILED`).

### Herramientas que usan las pruebas

**`pytest`.** Busca automáticamente las funciones cuyo nombre empieza con `test_` y las ejecuta. Una prueba **pasa si termina sin lanzar ninguna excepción**. Ojo: una prueba vacía también pasa, por eso toda prueba debe verificar algo.

**`assert`.** Verifica que algo sea verdadero. Si es falso, lanza un error y la prueba falla.

```python
assert costo == 0.002
```

**`pytest.raises`.** Verifica que el código dentro del bloque **sí lance** cierta excepción. Si no la lanza, la prueba falla.

```python
with pytest.raises(ValueError):
    algo_que_deberia_fallar()
```

**`Mock`.** Un objeto falso que se hace pasar por otro. Acepta cualquier atributo y tú decides qué devuelve.

```python
respuesta_falsa = Mock(status_code=401)   # una "respuesta HTTP" falsa con código 401
funcion = Mock(side_effect=ValueError())  # una función falsa que, al llamarla, lanza ValueError
```

`side_effect` define qué pasa al llamar al Mock: si es una excepción, la lanza. Además, el Mock **recuerda cómo lo llamaron**, y eso se puede verificar:

| Verificación | Qué confirma |
|---|---|
| `mock.assert_called_once()` | Se llamó exactamente una vez. |
| `mock.assert_not_called()` | No se llamó nunca. |

**`patch`.** Reemplaza **temporalmente** una función real por un Mock, solo mientras dura el bloque `with`.

```python
with patch("cliente.time.sleep") as mock_sleep:
    ...  # aquí time.sleep no espera de verdad
# aquí time.sleep vuelve a ser el real
```

La ruta se escribe **como se ve desde el módulo que la usa**: `"cliente.time.sleep"` es el `time.sleep` que usa `cliente.py`.

¿Por qué simular en vez de usar lo real?
- **No gasta tokens ni cuota.** La cuota gratuita es de unas 20 peticiones al día.
- **Es rápido.** No hay que esperar 2, 4 u 8 segundos reales.
- **Puedes forzar errores.** Un 401 o un 429 no se pueden provocar a voluntad contra la API real.

**Fixture con `autouse=True`.**

```python
@pytest.fixture(autouse=True)
def reiniciar_costo_total():
    cliente.costo_total_sesion = 0
    yield
```

La línea `@...` encima de una función es un **decorador**: le agrega un comportamiento. En este caso convierte la función en un *fixture*, código de preparación que pytest corre automáticamente **antes de cada prueba** gracias a `autouse=True`. Pone el costo acumulado en 0 para que una prueba no "contamine" a la siguiente. `yield` marca el punto donde se ejecuta la prueba; lo que viniera después correría al terminarla.

### Las 7 pruebas

#### `enviar_peticion` (en `src/consumir_gemini.py`)

| Prueba | Qué simula | Qué verifica |
|---|---|---|
| `test_enviar_peticion_credencial_invalida` | `requests.post` devuelve un código 401. | Que se lance `ValueError`. |
| `test_enviar_peticion_limite_de_uso` | `requests.post` devuelve un código 429. | Que se lance `TimeoutError`. |
| `test_enviar_peticion_exito` | Código 200 y `.json()` devuelve `{"texto": "respuesta simulada"}`. | Que la función devuelva ese mismo diccionario. |

En las tres se usa `patch("src.consumir_gemini.requests.post", ...)`, así que nunca sale nada a internet. La URL `https://ejemplo.invalid` es de relleno.

#### `con_reintento`

**`test_con_reintento_no_reintenta_value_error`**

```python
funcion = Mock(side_effect=ValueError("credencial inválida"))
with patch("cliente.time.sleep") as mock_sleep:
    with pytest.raises(ValueError):
        con_reintento(funcion)
funcion.assert_called_once()
mock_sleep.assert_not_called()
```

Una función falsa que siempre lanza `ValueError`. Verifica tres cosas:
1. El `ValueError` sale de `con_reintento`.
2. La función se llamó **una sola vez** (no hubo reintentos).
3. Nunca se esperó.

**`test_con_reintento_agota_intentos`**

```python
def siempre_falla():
    raise TimeoutError("simulado")

with patch("cliente.time.sleep"):
    with pytest.raises(TimeoutError):
        cliente.con_reintento(siempre_falla, intentos=3)
```

Una función que **siempre** lanza `TimeoutError`. Después de agotar los 3 intentos, `con_reintento` debe dejar salir el `TimeoutError`. `time.sleep` está simulado, así que la prueba no tarda 6 segundos reales.

#### `registrar_costo`

**`test_registrar_costo_acumula`**

```python
respuesta_falsa = {"usageMetadata": {"totalTokenCount": 1000}}
costo = cliente.registrar_costo(respuesta_falsa)
assert costo == cliente.COSTO_POR_1000_TOKENS
assert cliente.costo_total_sesion == cliente.COSTO_POR_1000_TOKENS
```

No necesita Mock porque `registrar_costo` no toca internet: basta un diccionario con la misma forma que la respuesta de Gemini. Con exactamente 1000 tokens, el costo debe ser igual a `COSTO_POR_1000_TOKENS`, y como el fixture dejó el total en 0, el acumulado también.

#### `consultar_modelo`

**`test_consultar_modelo_convierte_error`**

```python
with patch("cliente.con_reintento", side_effect=TimeoutError("simulado")):
    with pytest.raises(RuntimeError):
        consultar_modelo("pregunta de prueba")
```

Reemplaza `con_reintento` completo por un Mock que lanza `TimeoutError`, como si ya se hubieran agotado los intentos. Verifica que `consultar_modelo` lo convierta en `RuntimeError`.

### Qué no se prueba, y por qué

- **La API real:** sería lento, costoso y dependería de que Google esté disponible.
- **El número exacto de segundos de espera:** tiene un componente aleatorio (jitter), así que compararlo haría que la prueba falle al azar.

---

## 5. Resumen

| Función | Archivo | Qué hace | Lanza |
|---|---|---|---|
| `enviar_peticion` | `src/consumir_gemini.py` | Hace la petición HTTP y clasifica el error. | `ValueError` (401/403), `TimeoutError` (429/5xx), `RuntimeError` (otros) |
| `con_reintento` | `cliente.py` | Reintenta ante `TimeoutError` con esperas de 2 s, 4 s, 8 s… | El último `TimeoutError` si se agotan los intentos |
| `registrar_costo` | `cliente.py` | Calcula el costo por tokens y lo suma al total. | Nada |
| `consultar_modelo` | `cliente.py` | Une todo: arma, envía con reintentos, registra el costo y devuelve el texto. | `RuntimeError` (servicio caído), `ValueError` (configuración) |
