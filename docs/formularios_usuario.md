# Formularios del usuario

_Fecha: 2026-11-03 · Complementa [diseno_funcional.md](diseno_funcional.md)_

Este documento define los formularios con los que el usuario se registra y mantiene sus datos en el sistema. Cada campo indica la columna de la base de datos en la que se guarda.

**Principios que aplican a todos los formularios:**

- **Solo se pide lo que usan las reglas de elegibilidad.** No se piden RUT, nombres de los integrantes del hogar ni datos de salud.
- **"No sé" siempre es una respuesta válida** cuando el usuario puede no conocer el dato (porcentaje del RSH, tramo de Fonasa). El campo queda en `null` y el asistente puede orientar sobre cómo averiguarlo.
- **Las validaciones se hacen en el backend** (FastAPI), aunque el formulario también las haga en el navegador.
- **Los datos que el chat extrae de una conversación pasan por el mismo formulario de confirmación** antes de guardarse.

## Flujo de registro

```
F1 Crear cuenta ──► F2 Tu hogar ──► F3 Integrantes del hogar ──► F4 Revisa y confirma ──► Chat
   (usuario)          (hogar)          (integrante, repetible)       (resumen)

Después del registro:
   F5 Informar avance de un trámite     (tramite, paso_tramite, hogar)
   F6 Mis datos: editar, descargar o eliminar
```

F2 a F4 se pueden completar más tarde: el usuario puede chatear sin perfil, pero entonces el asistente solo entrega orientación general, sin diagnóstico personalizado.

---

## F1. Crear cuenta

```
┌──────────────────────────────────────────────────────────────┐
│  Crear cuenta                                       Paso 1/4 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Correo electrónico *                                        │
│  [__________________________________________]                │
│                                                              │
│  Contraseña *                                                │
│  [__________________________________________]                │
│  Mínimo 8 caracteres                                         │
│                                                              │
│  Repite la contraseña *                                      │
│  [__________________________________________]                │
│                                                              │
│  ¿Cómo quieres que te llamemos? (opcional)                   │
│  [__________________________________________]                │
│                                                              │
│  ────────────────────────────────────────────────────────    │
│  [ ] Autorizo el tratamiento de mis datos personales para    │
│      recibir orientación sobre beneficios. Puedo revocar     │
│      esta autorización y eliminar mis datos en cualquier     │
│      momento. (Ver política de datos) *                      │
│                                                              │
│  [ ] Entiendo que esta aplicación orienta, pero no realiza   │
│      trámites ni reemplaza la información oficial de         │
│      Fonasa, el Registro Social de Hogares o ChileAtiende. * │
│                                                              │
│                                          [ Crear cuenta ]    │
└──────────────────────────────────────────────────────────────┘
```

| Campo | Tipo | Obligatorio | Validación | Columna |
|---|---|---|---|---|
| Correo electrónico | email | Sí | Formato válido; único en el sistema | `usuario.email` |
| Contraseña | password | Sí | Mínimo 8 caracteres | `usuario.password_hash` (nunca en texto plano) |
| Repite la contraseña | password | Sí | Igual a la anterior | — (no se guarda) |
| Cómo te llamamos | texto | No | Máximo 50 caracteres | `usuario.nombre` |
| Autorización de datos | checkbox | Sí | Debe estar marcada | `usuario.consentimiento_datos` = `true`, `usuario.fecha_consentimiento` = ahora |
| Aviso de alcance | checkbox | Sí | Debe estar marcada | — (condición para continuar) |

---

## F2. Tu hogar

```
┌──────────────────────────────────────────────────────────────┐
│  Tu hogar                                           Paso 2/4 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Región *                                                    │
│  [ Selecciona una región                          ▼ ]        │
│                                                              │
│  Comuna *                                                    │
│  [ Selecciona una comuna                          ▼ ]        │
│                                                              │
│  ¿Tu hogar está inscrito en el Registro Social de Hogares? * │
│  ( ) Sí     ( ) No     ( ) No sé                             │
│                                                              │
│  ┌ Solo si respondiste "Sí" ──────────────────────────────┐  │
│  │ ¿En qué tramo de calificación está tu hogar?           │  │
│  │ [ 40% | 50% | 60% | 70% | 80% | 90% | 100% | No sé ▼ ] │  │
│  │                                                        │  │
│  │ Fecha de tu última cartola (mes y año)                 │  │
│  │ [ mm / aaaa ]                                          │  │
│  │ La encuentras en registrosocial.gob.cl con ClaveÚnica  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│                          [ Volver ]       [ Continuar ]      │
└──────────────────────────────────────────────────────────────┘
```

| Campo | Tipo | Obligatorio | Validación | Columna |
|---|---|---|---|---|
| Región | lista | Sí | Una de las 16 regiones | `hogar.region` |
| Comuna | lista dependiente de la región | Sí | Comuna de la región elegida | `hogar.comuna` |
| ¿Inscrito en el RSH? | opción única | Sí | Sí, No o No sé | — (controla los campos siguientes) |
| Tramo del RSH | lista | Solo si "Sí" | 40, 50, 60, 70, 80, 90, 100 o No sé | `hogar.porcentaje_rsh` (`null` si "No", "No sé" o sin respuesta) |
| Fecha de la cartola | mes y año | No | No puede ser futura | `hogar.fecha_cartola_rsh` |

Al guardar se crea la fila de `hogar` y se asigna a `usuario.hogar_id`. `hogar.actualizado_en` se registra automáticamente.

---

## F3. Integrantes del hogar

Formulario repetible: un bloque por persona. **El primer integrante es el propio usuario** (`parentesco = 'titular'`).

```
┌──────────────────────────────────────────────────────────────┐
│  Integrantes del hogar                              Paso 3/4 │
├──────────────────────────────────────────────────────────────┤
│  Incluye a todas las personas que viven contigo y comparten  │
│  gastos. No necesitamos sus nombres.                         │
│                                                              │
│  ┌ Integrante 1: Tú ──────────────────────────────────────┐  │
│  │ Fecha de nacimiento *          [ dd / mm / aaaa ]      │  │
│  │                                                        │  │
│  │ Previsión de salud *                                   │  │
│  │ [ Fonasa | Isapre | FF.AA. u Orden | Ninguna | No sé ▼]│  │
│  │                                                        │  │
│  │ Tramo de Fonasa (solo si es Fonasa)                    │  │
│  │ [ A | B | C | D | No sé                             ▼ ]│  │
│  │                                                        │  │
│  │ Situación laboral *                                    │  │
│  │ [ Trabajador dependiente                            ▼ ]│  │
│  │                                                        │  │
│  │ Ingreso mensual bruto aproximado *                     │  │
│  │ $ [____________]   Escribe 0 si no tiene ingresos      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌ Integrante 2 ────────────────────────────── [ Quitar ] ┐  │
│  │ Parentesco contigo *                                   │  │
│  │ [ Cónyuge o pareja                                  ▼ ]│  │
│  │ ... (mismos campos que el integrante 1)                │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  [ + Agregar integrante ]                                    │
│                                                              │
│                          [ Volver ]       [ Continuar ]      │
└──────────────────────────────────────────────────────────────┘
```

| Campo | Tipo | Obligatorio | Validación | Columna |
|---|---|---|---|---|
| Parentesco | lista | Sí (desde el integrante 2) | Cónyuge o pareja, Hijo o hija, Padre o madre, Hermano o hermana, Abuelo o abuela, Nieto o nieta, Otro familiar, Sin parentesco. El integrante 1 es siempre `titular` | `integrante.parentesco` |
| Fecha de nacimiento | fecha | Sí | No futura; edad entre 0 y 120 años | `integrante.fecha_nacimiento` |
| Previsión de salud | lista | Sí | Fonasa, Isapre, FF.AA. u Orden (Capredena, Dipreca), Ninguna, No sé | `integrante.prevision_salud` |
| Tramo de Fonasa | lista | Solo si la previsión es Fonasa | A, B, C, D o No sé | `integrante.tramo_fonasa` (`null` si no es Fonasa o "No sé") |
| Situación laboral | lista | Sí | Trabajador dependiente, Trabajador independiente, Cesante, Jubilado o pensionado, Estudiante, Labores del hogar, Otra | `integrante.situacion_laboral` |
| Ingreso mensual bruto | entero (pesos) | Sí | Mayor o igual a 0; sin puntos ni decimales | `integrante.ingreso_mensual` |

Notas:

- Se pide la **fecha de nacimiento** y no la edad, porque la edad cambia con el tiempo y algunas reglas dependen de ella (por ejemplo, cumplir 18 o 65 años).
- Se pide el **ingreso bruto** porque Fonasa clasifica por ingreso imponible, que se acerca más al bruto que al líquido. Es un valor **aproximado y declarado**: la aplicación no lo verifica.
- El formulario muestra un aviso si hay un menor de 18 años con ingresos mayores a 0 o con situación laboral "Jubilado o pensionado", pero permite guardar.

---

## F4. Revisa y confirma

```
┌──────────────────────────────────────────────────────────────┐
│  Revisa tus datos                                   Paso 4/4 │
├──────────────────────────────────────────────────────────────┤
│  Hogar                                          [ Editar ]   │
│  Biobío, Concepción · RSH: 60% (cartola 09/2026)             │
│                                                              │
│  Integrantes (3)                                [ Editar ]   │
│  • Tú: 38 años · Fonasa C · Dependiente · $850.000           │
│  • Cónyuge o pareja: 36 años · Fonasa B · Cesante · $0       │
│  • Hijo o hija: 9 años · Fonasa (carga) · Estudiante · $0    │
│                                                              │
│  Ingreso total del hogar: $850.000                           │
│                                                              │
│  Estos datos son declarados por ti. Úsalos solo para         │
│  orientarte; no reemplazan tu cartola ni tu certificado      │
│  de Fonasa.                                                  │
│                                                              │
│                          [ Volver ]       [ Confirmar ]      │
└──────────────────────────────────────────────────────────────┘
```

No tiene campos nuevos. Al confirmar, se guardan `hogar` e `integrante` en una sola transacción: si algo falla, no queda un perfil a medias.

**El mismo resumen se usa cuando el chat extrae datos.** Si el usuario escribe "ahora somos 4 en la casa", el asistente muestra este resumen con el cambio destacado y pregunta "¿Actualizo tus datos?" antes de guardar.

---

## F5. Informar avance de un trámite

Se abre desde la lista de trámites o desde el chat ("ya envié la solicitud", "me salió el resultado").

```
┌──────────────────────────────────────────────────────────────┐
│  Actualizar RSH por cambio de ingresos                       │
│  Iniciado el 03/11/2026                                      │
├──────────────────────────────────────────────────────────────┤
│  Pasos                                                       │
│  [x] 1. Reunir los documentos                                │
│      Finiquito o carta de despido                            │
│  [x] 2. Ingresar la solicitud con ClaveÚnica                 │
│  [ ] 3. Esperar la resolución                                │
│                                                              │
│  ¿En qué estado está? *                                      │
│  ( ) Pendiente: aún no empiezo                               │
│  ( ) En curso: estoy reuniendo documentos                    │
│  (•) Esperando respuesta: ya envié la solicitud              │
│  ( ) Aprobado                                                │
│  ( ) Rechazado                                               │
│                                                              │
│  ┌ Solo si es "Aprobado" y el trámite cambia tu perfil ───┐  │
│  │ Nuevo tramo del RSH                                    │  │
│  │ [ 40% | 50% | 60% | 70% | 80% | 90% | 100%          ▼ ]│  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Fecha de este avance *        [ dd / mm / aaaa ]            │
│                                                              │
│  Comentario (opcional)                                       │
│  [__________________________________________]                │
│                                                              │
│                                            [ Guardar ]       │
└──────────────────────────────────────────────────────────────┘
```

| Campo | Tipo | Obligatorio | Validación | Columna |
|---|---|---|---|---|
| Pasos completados | checkbox por paso | No | — | `paso_tramite.completado` |
| Estado | opción única | Sí | Pendiente, En curso, Esperando respuesta, Aprobado, Rechazado | `tramite.estado` |
| Nuevo dato del perfil | depende del trámite | Solo si es "Aprobado" y el trámite modifica el perfil | El mismo del formulario original (por ejemplo, F2 para el RSH) | `hogar.porcentaje_rsh`, `integrante.tramo_fonasa`, etc. |
| Fecha del avance | fecha | Sí | No futura; no anterior a `tramite.fecha_inicio` | `tramite.fecha_cierre` si es "Aprobado" o "Rechazado" |
| Comentario | texto | No | Máximo 500 caracteres | `tramite.motivo` |

Qué hace la aplicación al guardar:

| Estado nuevo | Acción |
|---|---|
| Esperando respuesta | Calcula la fecha esperada con el plazo del documento y la guarda en `tramite.plazo_esperado` |
| Aprobado | Actualiza el perfil (si corresponde), cierra el trámite, recalcula los beneficios y sugiere los siguientes trámites (`origen_tramite_id`) |
| Rechazado | Cierra el trámite y ofrece el trámite "Solicitar revisión", con las causas y el proceso de reclamo según el documento cargado |

---

## F6. Mis datos

```
┌──────────────────────────────────────────────────────────────┐
│  Mis datos                                                   │
├──────────────────────────────────────────────────────────────┤
│  Hogar e integrantes          Actualizado el 03/11/2026      │
│                                       [ Editar ]             │
│                                                              │
│  Descargar mis datos                                         │
│  Un archivo JSON con tu perfil, trámites y conversaciones.   │
│                                       [ Descargar ]          │
│                                                              │
│  Eliminar mi cuenta y mis datos                              │
│  Se borran tu perfil, trámites y conversaciones. Esta        │
│  acción no se puede deshacer.                                │
│                                       [ Eliminar ]           │
└──────────────────────────────────────────────────────────────┘
```

| Acción | Qué hace | Tablas |
|---|---|---|
| Editar | Abre F2 y F3 con los datos actuales y vuelve a pasar por F4 | `hogar`, `integrante` |
| Descargar | Genera un JSON con todos los datos del usuario | Todas las del usuario |
| Eliminar | Pide escribir "ELIMINAR" para confirmar y borra todo en una sola transacción | `usuario`, `hogar`, `integrante`, `tramite`, `paso_tramite`, `conversacion`, `mensaje`, `alerta` |

Descargar y eliminar responden a los derechos de acceso y de supresión de la Ley 21.719.
