# Análisis del negocio y de la documentación

_Fecha: 2026-10-30 · Alcance: estado actual del codebase (hasta el Módulo 2, Bloque 16)_

La idea es buena y tiene sentido para el Gate 3, pero hoy los documentos se contradicen entre sí y con el código, y hay cuatro riesgos de negocio que conviene resolver antes de entrar a la parte de RAG.

## 1. El negocio

**Qué es:** una "Plataforma de orientación ciudadana" que responde consultas sobre beneficios de salud (Fonasa, sus tramos A a D) y sociales (Registro Social de Hogares, RSH), con validación de RUT. El objetivo para el Gate 3 es un Agentic RAG con FastAPI y LangChain.

**Lo que está bien planteado:**
- El problema es real: la normativa de Fonasa y del RSH es confusa para la gente, y las respuestas del propio modelo confirman que el tema se presta a errores. Por ejemplo, en el benchmark el modelo aclara que al tramo B no se postula, sino que se asigna automáticamente.
- El banco de prompts ya anticipa la arquitectura del agente: el prompt `enrutador_agente_intentos` define las intenciones `CONSULTA_PERFIL`, `BUSQUEDA_RAG_NORMATIVA`, `GENERAR_REPORTE` y `CONVERSACIONAL`, que calzan directamente con los Bloques 18 a 23.
- El cambio de público objetivo está explicado y abierto a retroalimentación, lo que habla bien del proceso.

**Riesgos de negocio:**

| # | Riesgo | Evidencia en el repositorio |
|---|---|---|
| 1 | **El modelo inventa normativa.** En una aplicación de orientación, una cifra equivocada perjudica a la persona. | En `src/evaluacion_modelo.md`, el mismo modelo entrega umbrales distintos para el tramo B ($527.200 y "≈$500.000"). Además, afirma que a las personas "carentes de recursos… a veces las agrupa en B". Sin RAG sobre fuentes oficiales, el producto no es confiable. |
| 2 | **Datos personales sensibles.** El RUT, el porcentaje del RSH y el tramo de Fonasa son datos personales protegidos en Chile. | El prompt `extraer_datos_ciudadano` envía un RUT a Gemini en el nivel gratuito, donde, según sus términos, Google puede usar el contenido para mejorar sus productos (conviene confirmarlo). La Ley 21.719 de protección de datos entra en vigencia en diciembre de 2026. Esto alimenta directamente la matriz de riesgos del Bloque 32. |
| 3 | **No está definido de dónde provienen los datos del ciudadano.** El RSH y el tramo de Fonasa no tienen una API pública: se consultan con ClaveÚnica. | `decision-arquitectura.md` habla de "gestionar datos socioeconómicos de ciudadanos a nivel nacional", pero el único mecanismo existente es extraerlos de lo que escribe el usuario. Hace falta una decisión explícita: el usuario declara sus datos y la aplicación orienta, sin consultar fuentes oficiales. |
| 4 | **El argumento para excluir a las personas migrantes es débil.** | El Módulo 11 valida el dígito verificador, no la identidad, por lo que "validar la identidad de forma confiable" (README) promete más de lo que hace. Además, las personas extranjeras con residencia también tienen RUT. Una alternativa: aceptar a cualquier persona con RUT y ofrecer orientación normativa sin RUT, que es justamente la parte de RAG. |

**Tensión entre los requisitos y la operación:** la decisión de arquitectura exige "baja latencia para un chat fluido" y "escala multiusuario", pero elige un modelo con 7,28 s de latencia. Además, el ensayo de límite de uso muestra que el nivel gratuito permite 20 peticiones diarias por modelo. Hoy la restricción real es la cuota, no el costo.

## 2. Documentación

| Documento | Estado | Problemas concretos |
|---|---|---|
| `README.md` | Bien estructurado, con registro del ensayo de instalación limpia | Dice "`tests/`: pruebas (pendiente)", pero `test_cliente.py` y `test_pipeline.py` existen en la raíz. No menciona `pytest` ni los pipelines. `python cliente.py` no hace nada porque el bloque `__main__` está comentado. El enlace de Firebase a la ficha de alineación incluye un token de acceso público. |
| `docs/decision-arquitectura.md` | Contiene las 5 secciones que exige el curso | **Los precios no cuadran con el código:** la tabla indica $0,015/M de entrada para 3.5-flash-lite, mientras el código usa 0,0000003 por token, es decir, $0,30/M (20 veces más). El costo por petición ($0,0014785) se calcula con los precios del código, no con los de la tabla. Cita precios "al 01-01-2027", una fecha futura. La calidad se evaluó "a ojo", sin referencia, y califica de "excelente" a un modelo cuyas cifras varían entre ejecuciones. |
| `docs/diagrama_arquitectura.png` | Correcto para el Módulo 1 | Le falta toda la capa del Módulo 2 (`consultar_modelo`, `con_reintento`, `registrar_costo`), además de `systemInstruction`, `responseSchema` y `parsear_respuesta_json`. |
| `docs/registro_rate_limit.md` | Muy buen hallazgo (la cuota diaria) | Su conclusión sobre el backoff es incorrecta. Con `intentos=3` solo hay 2 esperas (2 s y 4 s); los 6,1–6,5 s registrados probablemente corresponden al total acumulado (2 + 4). El backoff funciona bien. El problema real es que, ante un `retryDelay` de ~7900 s, debería fallar de inmediato en lugar de reintentar. |
| `docs/clase_2026-10-27_…md` | Buena guía didáctica, pero sin commitear | Dice que `MODELO` cambió a `gemini-3.6-flash`, mientras que `cliente.py` usa actualmente `gemini-3.5-flash`. |
| `src/evaluacion_modelo.md` | Evidencia en bruto del benchmark, sin commitear | Debería commitearse y enlazarse desde la decisión de arquitectura, porque es su respaldo. |
| `.env.example` | Funciona | El comentario menciona "OpenAI o Hugging Face" y la variable se llama `API_KEY`, pero los mensajes de error del código dicen "Revisa tu GEMINI_API_KEY". |
| `requirements.txt` | Reproducible | `dotenv`, `google-genai` y `tenacity` no se usan. Además, `dotenv` está duplicado con `python-dotenv`. |
| Bloques 15 y 16 | Sin documentar | Las métricas de `resultados_metricas.json` usan los ejemplos del curso sobre Python, no casos del dominio del proyecto. |

**El modelo no coincide en ningún lado:** el README y la decisión de arquitectura eligen `gemini-3.5-flash-lite`, `cliente.py` usa `gemini-3.5-flash` y `consumir_gemini.py` usa `gemini-3.6-flash`. Además, la constante `MODELO` de `consumir_gemini.py` nunca se utiliza.

**Orden del repositorio:** `.env` está ignorado y nunca se commiteó. En cambio, `Gate1/`, `oop/` y `personal_demos/` no tienen relación con el producto, y conviene agregar `.playwright-mcp/` a `.gitignore`, ya que contiene el texto del curso con URLs firmadas que incluyen el correo del usuario.

## 3. Prioridades

1. **Unificar el modelo:** una sola constante que coincida con la decisión de arquitectura, y corregir la tabla de precios con la fuente y la fecha reales.
2. **Agregar una sección de alcance del producto en la decisión de arquitectura o en el README:** de dónde provienen los datos (declarados por el usuario), qué NO hace la aplicación (no consulta fuentes oficiales ni reemplaza a ChileAtiende) y cómo se trata el RUT (validarlo localmente con el Módulo 11 y no enviarlo al LLM, o enmascararlo).
3. **Rehacer las métricas del Bloque 16 con 3 a 5 casos de Fonasa y RSH**, con referencias tomadas de fonasa.cl o del sitio del RSH. Esto además sirve como base de evaluación para el RAG del Bloque 27.
4. **Actualizar el README** (pruebas, pytest, pipelines, la corrección de `cliente.py`) y el diagrama, incorporando la capa del Módulo 2.
5. **Commitear** `registro_rate_limit.md`, `evaluacion_modelo.md` y la guía de clase, corrigiendo la conclusión sobre el backoff.
6. **Revisar `con_reintento`** para que, ante un `retryDelay` largo (cuota diaria), falle de inmediato en lugar de reintentar.
