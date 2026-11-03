# Diseño funcional: asistente de beneficios Fonasa y RSH

_Fecha: 2026-11-03 · Estado: propuesta para el Gate 3 (todavía no implementada)_

## 1. Propósito

La normativa de Fonasa y del Registro Social de Hogares (RSH) es pública, así que **la información en sí no es el valor de la aplicación.** Una aplicación que solo responde preguntas generales no aporta nada frente a un chat general o una búsqueda en internet.

El valor está en **cruzar esa normativa con la situación concreta de cada persona** y convertir el resultado en acciones:

> Un asistente que conoce tu situación, la contrasta con documentos oficiales cargados y revisados, te dice qué te corresponde y qué hacer, y acompaña tus trámites.

| | Chat general | Esta aplicación |
|---|---|---|
| Conoce la normativa | De memoria: puede estar desactualizada o inventada | Solo a partir de los documentos oficiales cargados, con fecha y fuente |
| Conoce al usuario | No; hay que explicar la situación cada vez | Sí: hogar, tramo, porcentaje del RSH, trámites en curso |
| Recuerda lo que pasó | No | Historial de conversaciones y trámites |
| Calcula si corresponde un beneficio | Lo estima en texto | Lo calcula con reglas fijas sobre datos reales |
| Reconoce lo que no sabe | Rara vez | Sí: si no hay documento cargado sobre el tema, lo dice |

**Lo que la aplicación no hace:** no consulta fuentes oficiales en nombre del usuario (Fonasa y el RSH no tienen API pública), no realiza trámites y no reemplaza a ChileAtiende. Orienta, prepara y acompaña.

## 2. Las tres piezas

| Pieza | Responde a | Contenido |
|---|---|---|
| **Base de datos relacional** | ¿Quién es esta persona? | Hechos sobre el usuario: hogar, integrantes, ingresos, tramo, porcentaje del RSH, trámites |
| **RAG** | ¿Qué dice la norma? | Fragmentos de los documentos oficiales cargados manualmente en `normativa/` |
| **Agente** | ¿Qué significa para esta persona? | Elige las herramientas, cruza ambas fuentes y redacta la respuesta |

**Para qué sirve el RAG:** no es el producto, sino la garantía de que la respuesta es correcta.

1. **Evita que el modelo invente.** En el benchmark (`src/evaluacion_modelo.md`), el mismo modelo dio dos umbrales distintos para el tramo B: $527.200 y "≈$500.000".
2. **Permite citar la fuente** y la fecha del documento en cada afirmación.
3. **Deja el contenido bajo control:** la aplicación solo sabe lo que se cargó y revisó.

**Reglas de diseño:**

- Los umbrales y las reglas de elegibilidad viven en la tabla `regla_elegibilidad`, **nunca en el LLM**. El LLM busca la norma y la explica; Python decide si corresponde un beneficio.
- **Si el RAG no encuentra fragmentos relevantes, la respuesta es "no tengo información cargada sobre eso"**, nunca una respuesta desde la memoria del modelo. Va en la instrucción de sistema y se verifica con casos de prueba.
- **Cada respuesta muestra el documento y su fecha:** "Según *Acreditación de carentes de recursos* (Fonasa, descargado el 2026-11-03)".

## 3. Flujo de una consulta

Fonasa y el RSH son **sistemas independientes**: distintas instituciones, distintos criterios y distinta forma de actualizarse.

| | Fonasa | RSH |
|---|---|---|
| Clasifica | A cada afiliado, en tramos A, B, C y D | A cada hogar, en tramos de porcentaje |
| Criterio | Ingreso imponible mensual y cargas familiares | Situación socioeconómica del hogar |
| Actualización | Automática, una vez al año, según las cotizaciones del año anterior | La solicita el hogar ante un cambio |

El tramo de Fonasa **no se calcula** con el porcentaje del RSH. Se tocan en pocos puntos; por ejemplo, el certificado del RSH es uno de los documentos de respaldo para acreditarse como carente de recursos (tramo A). El valor de la aplicación es que **un mismo evento de vida afecta a ambos sistemas a la vez**, y la aplicación ordena los dos caminos en paralelo.

Ejemplo: el usuario escribe *"Perdí mi trabajo, ¿qué me cambia?"*

```
1. Enrutador          → intención: CONSULTA_PERFIL + BUSQUEDA_RAG_NORMATIVA
2. Herramienta SQL    → perfil: hogar de 3 personas, afiliado en tramo C, hogar en el 60% del RSH
3. Herramienta RAG    → RSH:    actualización del registro por cambio de ingresos
                        Fonasa: acreditación como carente de recursos (requisitos y documentos);
                                paso automático al tramo A tras 12 meses sin cotizaciones
4. Reglas en código   → evalúa por separado qué aplica en cada sistema (cálculo determinista)
5. LLM redacta        → "Tu situación cambia en dos frentes independientes:
                        • RSH: actualiza tu registro declarando el cambio de ingresos; un nuevo
                          porcentaje puede abrirte bonos y subsidios.
                        • Fonasa: puedes acreditarte como carente de recursos (tramo A, atención
                          gratuita en la red pública). Necesitas: ...
                        Fuentes: [documento, fecha] [documento, fecha]"
6. Base de datos      → crea dos trámites independientes en estado pendiente,
                        con sus pasos copiados desde paso_plantilla
```

Herramientas del agente:

| Herramienta | Tipo | Qué hace |
|---|---|---|
| `consultar_perfil` | SQL | Lee `usuario`, `hogar` e `integrante` |
| `buscar_normativa` | RAG | Recupera fragmentos del vector store con su `documento_id` |
| `evaluar_elegibilidad` | Reglas en Python | Aplica `regla_elegibilidad` sobre el perfil |
| `gestionar_tramite` | SQL | Crea un trámite (copiando sus pasos desde `paso_plantilla`) o actualiza su estado |
| `generar_reporte` | LLM + SQL | Resumen de la situación del usuario para llevar a la oficina |

## 4. Ciclo de vida de un trámite

Un trámite guardado solo tiene sentido si algo lo usa después. Estos son los estados posibles:

```
pendiente ──► en_curso ──► esperando_respuesta ──┬──► aprobado ──► actualiza el perfil
                                                 │                  └► recalcula beneficios
                                                 │                  └► sugiere trámites nuevos
                                                 │                     (origen_tramite_id)
                                                 └──► rechazado ──► RAG: causas y reclamo
                                                                    └► trámite "Solicitar revisión"
```

Ejemplo (los días se cuentan desde que el usuario abre el chat):

| Momento | Evento | Qué hace la aplicación |
|---|---|---|
| Día 0 | El usuario cuenta que perdió el trabajo | Crea dos trámites: "Actualizar RSH" y "Acreditarse como carente de recursos en Fonasa", cada uno con sus pasos y documentos |
| Día 2 | El usuario vuelve al chat | Retoma: "En el RSH te falta el paso 2: ingresar la solicitud" |
| Día 3 | El usuario dice "ya la envié" | El trámite del RSH pasa a `esperando_respuesta` y se calcula la fecha esperada con el plazo del RAG |
| Día 20 | El usuario informa "me salió 40%" | Actualiza `hogar.porcentaje_rsh`, cierra el trámite, recalcula **solo los beneficios que dependen del RSH** y crea los trámites siguientes (con `origen_tramite_id`). En el trámite de Fonasa, marca como disponible el documento "certificado RSH actualizado" |

El resultado del RSH **no cambia el tramo de Fonasa**. Solo aporta un documento de respaldo al trámite de Fonasa, que sigue su propio camino.

La información útil que sale del trámite:

| Información | Para qué sirve |
|---|---|
| **Estado** | Retomar la conversación con contexto, sin que el usuario recuerde en qué iba |
| **Resultado** | Actualizar el perfil, recalcular beneficios y generar los siguientes trámites |
| **Plazos** | Recordarle al usuario, cuando vuelve, que algo se atrasó |

**Limitación:** la aplicación no ve el estado real en Fonasa ni en el RSH. Depende de que el usuario informe sus avances con el formulario de avance (ver `docs/formularios_usuario.md`).

## 5. Funcionalidades, por valor diferencial

1. **Diagnóstico de beneficios:** qué te corresponde con tu perfil y qué no estás usando.
2. **Plan de acción con seguimiento:** pasos, documentos y plazos de cada trámite.
3. **Simulador:** "si mi mamá se viene a vivir conmigo, ¿qué cambia?".
4. **Reporte para la oficina** (intención `GENERAR_REPORTE`).
5. **Continuidad** entre sesiones.
6. **Alertas por plazo o por cambio de un documento** (trabajo futuro, ver la sección 9).

## 6. Administración de la normativa: carga manual

Para el prototipo, **los documentos se cargan a mano en el repositorio**. No hay monitoreo de URLs ni descarga automática: el administrador decide qué documentos existen y cuándo se actualizan.

### Dos tipos de datos

| Tipo | Tablas | Quién lo alimenta | Cada cuánto cambia |
|---|---|---|---|
| **Catálogo** (las reglas) | `documento_normativo`, `beneficio`, `regla_elegibilidad`, `paso_plantilla` | El administrador, desde archivos en `normativa/` | Cuando cambia una norma |
| **Datos del usuario** | `usuario`, `hogar`, `integrante`, `tramite`, `paso_tramite`, `conversacion`, `mensaje`, `alerta` | El usuario (formularios y chat) y la propia aplicación | A diario |

### Estructura en el repositorio

```
normativa/
├── fonasa/
│   ├── acreditacion_carentes_recursos.pdf    ← documento oficial, descargado a mano
│   └── acreditacion_carentes_recursos.yaml   ← metadatos, beneficios, reglas y pasos
└── rsh/
    ├── actualizacion_por_cambio_ingresos.pdf
    └── actualizacion_por_cambio_ingresos.yaml
```

Cada documento va acompañado de un YAML que escribe el administrador:

```yaml
documento:
  titulo: "Acreditación de carentes de recursos"
  institucion: Fonasa
  url_origen: https://www.fonasa.cl/...   # solo como referencia para el usuario
  descargado_en: 2026-11-03

beneficios:
  - nombre: "Tramo A de Fonasa (carente de recursos)"
    descripcion: "Atención gratuita en la red pública"
    reglas:
      - { campo: ingreso_mensual, operador: "==", valor: 0 }   # TODO: verificar en el documento
    pasos:
      - { descripcion: "Reunir los documentos", documento_requerido: "Cédula, certificado de cotizaciones AFP (12 meses), certificado RSH" }
      - { descripcion: "Solicitar la acreditación en Fonasa" }
      - { descripcion: "Esperar la resolución" }
```

**El LLM puede ayudar a redactar el YAML** (por ejemplo, extrayendo requisitos del PDF con `responseSchema`), pero **cada valor lo revisa el administrador contra el documento antes de hacer commit.** Un umbral mal escrito hace que la aplicación le diga a alguien que le corresponde algo que no le corresponde.

### Carga

```bash
python -m app.cargar_normativa
```

Por cada documento de `normativa/`:

1. Calcula el hash del archivo. **Si no cambió desde la última carga, lo salta**, para no reindexar lo que no cambió.
2. Extrae el texto, lo divide en fragmentos y los guarda en el vector store, con `documento_id` en la metadata.
3. Inserta o actualiza `documento_normativo`, `beneficio`, `regla_elegibilidad` y `paso_plantilla` desde el YAML.

### Cuando cambia una norma

1. El administrador descarga el documento nuevo y reemplaza el archivo.
2. Actualiza el YAML.
3. Hace commit y vuelve a correr la carga.

**Git es el historial de versiones:** `git log normativa/fonasa/` muestra qué cambió, cuándo y por qué. La revisión de un cambio es un pull request: se compara el diff del YAML contra el documento oficial antes de mergear.

### Los tres roles de `documento_normativo`

| Rol | Cómo lo cumple |
|---|---|
| **Detectar si hay que reindexar** | `hash_contenido` del archivo |
| **Citar la fuente** | Cada fragmento del vector store lleva `documento_id`; la respuesta muestra `titulo`, `institucion` y `descargado_en` |
| **Saber qué revisar cuando cambia** | `beneficio.documento_id`: al reemplazar un documento, se sabe qué beneficios, reglas y pasos dependen de él |

## 7. Modelo de datos

```
┌──────────────────────────┐          ┌──────────────────────────┐          ┌──────────────────────────┐
│ integrante               │          │ hogar                    │          │ mensaje                  │
├──────────────────────────┤          ├──────────────────────────┤          ├──────────────────────────┤
│ PK id                    │ N      1 │ PK id                    │          │ PK id                    │
│ FK hogar_id              │──────────│    region                │          │ FK conversacion_id       │
│    parentesco            │          │    comuna                │          │    rol                   │
│    fecha_nacimiento      │          │    porcentaje_rsh (null) │          │    contenido             │
│    prevision_salud       │          │    fecha_cartola_rsh     │          │    intent                │
│    tramo_fonasa  (null)  │          │    actualizado_en        │          │    creado_en             │
│    situacion_laboral     │          └──────────────────────────┘          └──────────────────────────┘
│    ingreso_mensual       │                       │1                                    │N
└──────────────────────────┘                       │                                     │
                                                   │                                     │
                                                   │                                     │
                                                   │                                     │
                                                   │N                                    │1
┌──────────────────────────┐          ┌──────────────────────────┐          ┌──────────────────────────┐
│ alerta                   │          │ usuario                  │          │ conversacion             │
├──────────────────────────┤          ├──────────────────────────┤          ├──────────────────────────┤
│ PK id                    │ N      1 │ PK id                    │ 1      N │ PK id                    │
│ FK usuario_id            │──────────│ FK hogar_id              │──────────│ FK usuario_id            │
│ FK tramite_id   (null)   │          │    email                 │          │    iniciada_en           │
│    tipo                  │          │    password_hash         │          └──────────────────────────┘
│    mensaje               │          │    nombre        (null)  │
│    leida                 │          │    consentimiento_datos  │
│    creado_en             │          │    fecha_consentimiento  │
└───────────────────│N─────┘          │    creado_en             │
                    │                 └──────────────────────────┘
                    │                              │1
                    │                              │
                    │                              │
                    │                              │
                    │                              │N
                    │                 ┌──────────────────────────┐          ┌──────────────────────────┐
                    │                 │ tramite                  │          │ paso_tramite             │
                    │                 ├──────────────────────────┤          ├──────────────────────────┤
                    │                 │ PK id                    │ 1      N │ PK id                    │
                    │                 │ FK usuario_id            │──────────│ FK tramite_id            │
                    │                 │ FK beneficio_id (null)   │          │    orden                 │
                    │               1 │ FK origen_tramite_id     │          │    descripcion           │
                    └─────────────────│    tipo                  │          │    documento_requerido   │
                                      │    estado                │          │    completado            │
                                      │    motivo                │          └──────────────────────────┘
                                      │    plazo_esperado        │──┐
                                      │    fecha_inicio          │  │ 1:N origen (cadena)
                                      │    fecha_cierre          │<─┘
                                      └──────────────────────────┘
                                                   │N
                                                   │
                                                   │
                                                   │
                                                   │1
┌──────────────────────────┐          ┌──────────────────────────┐          ┌──────────────────────────┐
│ documento_normativo      │          │ beneficio                │          │ regla_elegibilidad       │
├──────────────────────────┤          ├──────────────────────────┤          ├──────────────────────────┤
│ PK id                    │ 1      N │ PK id                    │ 1      N │ PK id                    │
│    archivo               │──────────│ FK documento_id          │──────────│ FK beneficio_id          │
│    titulo                │          │    nombre                │          │    campo                 │
│    institucion           │          │    institucion           │          │    operador              │
│    url_origen            │          │    descripcion           │          │    valor                 │
│    descargado_en         │          └──────────────────────────┘          └──────────────────────────┘
│    hash_contenido        │                       │1
│    cargado_en            │                       │
└──────────────────────────┘                       │
             │1                                    │
             │                                     │
             │N                                    │N
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐           ┌──────────────────────────┐
  vector store (RAG)                  │ paso_plantilla           │
  chunk + embedding                   ├──────────────────────────┤
  metadata: documento_id              │ PK id                    │─ ─ ─ ► se copia a paso_tramite
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘           │ FK beneficio_id          │        al crear el trámite
                                      │    orden                 │
                                      │    descripcion           │
                                      │    documento_requerido   │
                                      └──────────────────────────┘
```

### Zonas

| Zona | Tablas | Qué guarda |
|---|---|---|
| **Persona** | `usuario`, `hogar`, `integrante` | La situación del usuario. Las reglas de Fonasa y del RSH se evalúan por hogar o por afiliado, por eso los ingresos, la previsión y el tramo están en `integrante`. El propio usuario es un integrante más (`parentesco = 'titular'`). |
| **Catálogo** | `documento_normativo`, `beneficio`, `regla_elegibilidad`, `paso_plantilla` | Las reglas, cargadas desde `normativa/`. Cada beneficio apunta al documento que lo respalda. |
| **Seguimiento** | `tramite`, `paso_tramite`, `alerta` | El proceso que la aplicación acompaña. |
| **Chat** | `conversacion`, `mensaje` | El historial para retomar conversaciones. `intent` guarda la decisión del enrutador. |

### Relaciones clave

- **`tramite.origen_tramite_id`** (relación consigo misma): la cadena de trámites. Un trámite aprobado genera los siguientes, y cada uno apunta a su origen.
- **`tramite.beneficio_id`** (nullable): el beneficio que desbloquea el trámite. Algunos trámites, como actualizar el RSH, no son un beneficio en sí mismos.
- **`paso_plantilla` → `paso_tramite`**: al crear un trámite, sus pasos se **copian** desde la plantilla del beneficio. Se copian, no se referencian, para que un trámite en curso no cambie si después se actualiza la plantilla.
- **`regla_elegibilidad`**: los umbrales como datos (`campo`, `operador`, `valor`). Ejemplo: `ingreso_mensual <= <tope del tramo B vigente>`. Python los evalúa sobre `integrante` y `hogar`. Cada valor sale del documento cargado; nunca se escribe de memoria. Por ejemplo, las fuentes de 2026 no coinciden en el tope del tramo B ($500.000, $529.000 o $539.000).
- **`hogar.porcentaje_rsh` e `integrante.tramo_fonasa`** son independientes: ninguna regla calcula uno a partir del otro. Ambos son nullable porque el usuario puede no saberlos.
- **`documento_normativo` → vector store**: los fragmentos del RAG viven fuera de la base relacional, con el `documento_id` en su metadata.
- **`alerta.tramite_id`**: en el prototipo, las alertas solo nacen de trámites (por ejemplo, un plazo vencido que se muestra cuando el usuario vuelve).

## 8. Datos personales

`integrante` guarda ingresos, situación laboral y previsión, que son datos personales bajo la Ley 21.719 (vigente desde diciembre de 2026).

- El usuario **declara** sus datos y da su **consentimiento explícito** (`usuario.consentimiento_datos`, `fecha_consentimiento`).
- Se guarda **solo lo que usan las reglas**. Los integrantes se identifican por parentesco, sin nombres.
- **No se envían identificadores al LLM**: solo los campos que necesita la consulta ("hogar de 3, ingresos X"), nunca nombre, email ni RUT.
- La aplicación **no pide RUT** ni datos de salud (como enfermedades crónicas) en el prototipo.
- Si el chat extrae datos del perfil ("somos 4 y gano 600 mil"), **la aplicación pide confirmación antes de guardar**. La salida del LLM nunca se escribe directo en la base.
- El usuario puede **descargar o eliminar** sus datos (ver `docs/formularios_usuario.md`).

## 9. Alcance para el Gate 3

| Incluir | Dejar como trabajo futuro |
|---|---|
| Formularios de registro, hogar e integrantes, con consentimiento | Alertas por plazo con un proceso diario |
| Carga manual de documentos en `normativa/` y su comando de carga | Descarga automática y monitoreo de URLs de las fuentes |
| RAG con citas y respuesta "no tengo información cargada" | Alertas a usuarios cuando cambia un documento |
| `evaluar_elegibilidad` con reglas en tabla | Simulador "qué pasaría si" |
| Trámite con pasos desde `paso_plantilla`; un resultado actualiza el perfil y sugiere los siguientes | Reporte para la oficina |
| Historial de conversación | Panel web de administración del catálogo |

Pendiente de decidir cuando lleguen los Bloques 24 a 28: cómo extraer el texto de los PDF, qué embeddings usar y qué vector store, siguiendo las convenciones del curso.

Relación con el curso:

| Bloque | Pieza |
|---|---|
| 15–17 Evaluación | Métricas y revisión manual con casos de Fonasa y del RSH |
| 21–23 Agentes | Enrutador y herramientas `consultar_perfil`, `buscar_normativa`, `evaluar_elegibilidad`, `gestionar_tramite` |
| 24–28 RAG | Carga de `normativa/`, fragmentos, embeddings y citas |
| 31–32 Seguridad | Minimización de datos, prompt injection y matriz de riesgos |
| Módulo 3 | FastAPI (endpoints de formularios, chat y trámites), base de datos en Docker |
