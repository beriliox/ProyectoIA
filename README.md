# Plataforma de orientación ciudadana (Chile) — Especialización en Desarrollo con IA Generativa (Accenture)

> En la propuesta inicial [Ficha de Alineación Técnica y elige tu ruta [Core]](https://firebasestorage.googleapis.com/v0/b/skillnest-firebase-5bb2a.firebasestorage.app/o/actividades%2F6ac69ded3d0032b69e454385%2F1791732873085-e2fe0ce61c8427fb-Ficha_Alineacion_CarloEcheverria.docx?alt=media&token=a55e41ca-1689-423d-9c9a-c7d4f3921ebd), la aplicación estaba pensada para personas migrantes: orientarlas en su proceso de regularización o ayudarlas a entender su situación actual. En esta versión cambié el público objetivo a **ciudadanos chilenos**.
>
> **¿Por qué lo cambié?**
>
> 1. **Puedo validar la identidad de forma confiable.** El RUT chileno tiene una estructura conocida y un dígito verificador que se calcula con el algoritmo Módulo 11. Eso me permite validar en el backend (FastAPI) que el dato ingresado es correcto antes de procesar la consulta.
> 2. **Con usuarios migrantes no tenía esa certeza.** Muchas personas en proceso de regularización todavía no tienen RUT o usan identificadores provisorios, y no tenía una regla clara para validarlos.
> 3. **El alcance queda más claro.** Al trabajar con ciudadanos chilenos, el foco está en beneficios como Fonasa y el Registro Social de Hogares (RSH), con normativa bien definida para la búsqueda en el flujo de Agentic RAG.
>
> **Abierto a retroalimentación:** este cambio es una propuesta, no una decisión cerrada. Si como evaluadores del proyecto ven una mejor forma de abordarlo (por ejemplo, volver a incluir a personas migrantes con otro mecanismo de validación), estoy abierto a ajustarlo.

---

Proyecto del programa que consume la API de **Google Gemini** para construir una miniaplicación de orientación ciudadana sobre datos sociales y de salud en Chile (RUT, porcentaje del RSH, tramo de Fonasa). El objetivo final (Gate 3) es un flujo de Agentic RAG con FastAPI y LangChain con Tool Calling.

Modelo elegido: **`gemini-3.5-flash-lite`** (ver [docs/decision-arquitectura.md](docs/decision-arquitectura.md)).

## Cómo replicar el ambiente en local

### Requisitos previos

- **Python 3** (el proyecto se probó con Python 3.14). Verifica tu versión con `python3 --version`.
- **Git**, para clonar el repositorio.
- **Una llave de API de Gemini**, que se obtiene gratis en [Google AI Studio](https://aistudio.google.com/apikey) con una cuenta de Google.
- Conexión a Internet: todos los scripts hacen peticiones a la API de Gemini.

### 1. Clonar el repositorio

```bash
git clone https://github.com/beriliox/ProyectoIA.git
cd ProyectoIA
```

### 2. Crear y activar el entorno virtual

Cada proyecto usa su propio entorno virtual. La carpeta `venv/` ya está excluida en `.gitignore`.

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

Sabrás que está activo porque la terminal muestra `(venv)` al inicio de la línea. Para salir del entorno, usa `deactivate`.

### 3. Instalar las dependencias

Con el entorno virtual activo:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar las variables de entorno

Copia la plantilla y completa tu llave:

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Abre `.env` y reemplaza el valor de ejemplo:

```env
API_KEY=tu_llave_de_gemini
```

El código lee esta variable con `python-dotenv` al importar `src/consumir_gemini.py`. El archivo `.env` nunca se sube al repositorio.

### 5. Verificar que todo funciona

Desde la raíz del repositorio, con el entorno virtual activo:

```bash
python src/consumir_gemini.py
```

Si la configuración es correcta, verás la latencia, el costo de la petición y una respuesta JSON con las claves `categoria` y `nivel`.

## Cómo ejecutar

Todos los comandos se ejecutan desde la raíz del repositorio.

| Comando | Qué hace |
|---|---|
| `python src/consumir_gemini.py` | Petición de prueba a Gemini con `response_schema`; imprime latencia, costo y el JSON parseado. |
| `python src/evaluacion_modelos.py` | Benchmark de 3 modelos Gemini (4 repeticiones c/u): latencia por intento, latencia promedio y costo acumulado. |
| `python src/consistencia.py` | Ejecuta cada prompt de `src/prompts/banco.py` 3 veces, valida que la respuesta tenga las claves esperadas y guarda el resultado en `docs/registro_resultados.json`. |
| `python src/precision.py` | Calcula precisión, recall y F1 por consulta y guarda los resultados en `docs/resultados_metricas.json`. |
| `python src/cliente.py` | Envía una petición con reintentos (`con_reintento`) ante límite de uso (429) o errores del servidor (5xx). |

## Estructura de carpetas

- `src/` : código fuente.
  - `consumir_gemini.py` : cliente HTTP para Gemini (`armar_peticion`, `enviar_peticion`, `extraer_texto`, `calcular_costo`, `parsear_respuesta_json`). Traduce los errores HTTP a excepciones: `ValueError` (401/403), `TimeoutError` (429/5xx), `RuntimeError` (conexión, timeout, otros).
  - `evaluacion_modelos.py` : comparación de latencia y costo entre `gemini-3.6-flash`, `gemini-3.5-flash-lite` y `gemini-3.1-flash-lite`.
  - `consistencia.py` : prueba de consistencia de las respuestas estructuradas (JSON).
  - `prompts/banco.py` : banco de prompts (`evaluar_orientacion_ciudadana`, `extraer_datos_ciudadano`, `enrutador_agente_intentos`), cada uno con su `system_instruction`, ejemplo de usuario, claves esperadas y `response_schema`.
  - `prompts/respuestas.md` : respuestas de ejemplo obtenidas por cada prompt.
  - `cliente.py` : ejemplo de petición con reintentos.
  - `precision.py` : métricas de precisión, recall y F1.
- `docs/` : documentación técnica.
  - `decision-arquitectura.md` : comparación de modelos y justificación de la elección.
  - `diagrama_arquitectura.png` : diagrama de arquitectura.
  - `evidencia_peticion_autenticada.png` : evidencia de una petición autenticada exitosa.
  - `registro_resultados.json` : resultados de la última corrida de consistencia.
  - `resultados_metricas.json` : métricas de precisión por consulta.
  - `clase_2026-10-27_cliente_y_pruebas.md` : apuntes de la clase sobre cliente y pruebas.
- `tests/` : pruebas unitarias (`test_cliente.py`, `test_pipeline.py`).
- `requirements.txt` : dependencias de Python (`requests`, `python-dotenv`, `google-genai`, `tenacity`, entre otras).
- `.env.example` : plantilla de variables de entorno (`API_KEY`), sin valores reales.
- `.gitignore` : excluye el entorno virtual y el archivo `.env`.

## Resultados actuales

- **Consistencia:** 3/3 respuestas JSON válidas en cada uno de los 3 prompts del banco.
- **Benchmark:** `gemini-3.5-flash-lite` obtuvo 7,28 s de latencia promedio, con el mejor equilibrio entre detalle normativo y costo. El detalle está en `docs/decision-arquitectura.md`.

## Reglas que se mantienen durante todo el programa

- Ningún secreto (contraseña, llave de API, token) va escrito directamente en el código ni en ningún archivo que se suba al repositorio.
- Cada proyecto nuevo tiene su propio entorno virtual: no se comparten dependencias entre proyectos distintos.
- Todo el trabajo que se entrega en este programa vive en un repositorio de GitHub, sin excepción.

## Registro del ensayo de instalación limpia

### 2026-10-24 — Dependencia faltante

- **Encontrado:** faltaba `dotenv` en `requirements.txt` (estaba instalado a mano).
- **Corregido:** agregado con `pip freeze > requirements.txt` y commiteado.
- **Resultado tras la corrección:** el proyecto corre sin intervención manual.

### 2026-10-24 — Llamado a `armar_peticion`

- **Encontrado:** llamado al método `armar_peticion` en el script `evaluacion_modelos.py`.
- **Corregido:** se agregan los parámetros faltantes `system_instruction` y `response_schema` al método.
- **Resultado tras la corrección:** el proyecto corre sin intervención manual.
