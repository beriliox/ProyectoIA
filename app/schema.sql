-- Esquema de la base de datos (ver docs/diseno_funcional.md, sección 7).
-- SQL estándar para que migrar a PostgreSQL más adelante sea acotado.
-- Fechas en texto ISO 8601 (AAAA-MM-DD); booleanos como 0/1.

-- ── Catálogo: se carga desde normativa/ ──────────────────────────────

CREATE TABLE IF NOT EXISTS documento_normativo (
    id              INTEGER PRIMARY KEY,
    archivo         TEXT NOT NULL UNIQUE,
    titulo          TEXT NOT NULL,
    institucion     TEXT NOT NULL,
    url_origen      TEXT,
    descargado_en   TEXT NOT NULL,
    hash_contenido  TEXT NOT NULL,
    cargado_en      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS beneficio (
    id              INTEGER PRIMARY KEY,
    documento_id    INTEGER NOT NULL REFERENCES documento_normativo (id),
    nombre          TEXT NOT NULL,
    institucion     TEXT NOT NULL,
    descripcion     TEXT
);

CREATE TABLE IF NOT EXISTS regla_elegibilidad (
    id              INTEGER PRIMARY KEY,
    beneficio_id    INTEGER NOT NULL REFERENCES beneficio (id) ON DELETE CASCADE,
    campo           TEXT NOT NULL,
    operador        TEXT NOT NULL CHECK (operador IN ('==', '!=', '<', '<=', '>', '>=')),
    valor           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paso_plantilla (
    id                   INTEGER PRIMARY KEY,
    beneficio_id         INTEGER NOT NULL REFERENCES beneficio (id) ON DELETE CASCADE,
    orden                INTEGER NOT NULL,
    descripcion          TEXT NOT NULL,
    documento_requerido  TEXT,
    UNIQUE (beneficio_id, orden)
);

-- ── Persona: se llena con los formularios F1 a F4 ─────────────────────

CREATE TABLE IF NOT EXISTS hogar (
    id                 INTEGER PRIMARY KEY,
    region             TEXT NOT NULL,
    comuna             TEXT NOT NULL,
    porcentaje_rsh     INTEGER CHECK (porcentaje_rsh IN (40, 50, 60, 70, 80, 90, 100)),
    fecha_cartola_rsh  TEXT,
    actualizado_en     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS integrante (
    id                 INTEGER PRIMARY KEY,
    hogar_id           INTEGER NOT NULL REFERENCES hogar (id) ON DELETE CASCADE,
    parentesco         TEXT NOT NULL CHECK (parentesco IN (
                           'titular', 'conyuge_pareja', 'hijo', 'padre_madre', 'hermano',
                           'abuelo', 'nieto', 'otro_familiar', 'sin_parentesco')),
    fecha_nacimiento   TEXT NOT NULL,
    prevision_salud    TEXT NOT NULL CHECK (prevision_salud IN (
                           'fonasa', 'isapre', 'ffaa_orden', 'ninguna', 'no_sabe')),
    tramo_fonasa       TEXT CHECK (tramo_fonasa IN ('A', 'B', 'C', 'D')),
    situacion_laboral  TEXT NOT NULL CHECK (situacion_laboral IN (
                           'dependiente', 'independiente', 'cesante', 'jubilado_pensionado',
                           'estudiante', 'labores_hogar', 'otra')),
    ingreso_mensual    INTEGER NOT NULL CHECK (ingreso_mensual >= 0),
    -- el tramo solo tiene sentido para afiliados a Fonasa
    CHECK (tramo_fonasa IS NULL OR prevision_salud = 'fonasa')
);

CREATE TABLE IF NOT EXISTS usuario (
    id                    INTEGER PRIMARY KEY,
    hogar_id              INTEGER REFERENCES hogar (id) ON DELETE SET NULL,
    email                 TEXT NOT NULL UNIQUE,
    password_hash         TEXT NOT NULL,
    nombre                TEXT,
    consentimiento_datos  INTEGER NOT NULL CHECK (consentimiento_datos = 1),
    fecha_consentimiento  TEXT NOT NULL,
    creado_en             TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ── Seguimiento ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS tramite (
    id                 INTEGER PRIMARY KEY,
    usuario_id         INTEGER NOT NULL REFERENCES usuario (id) ON DELETE CASCADE,
    beneficio_id       INTEGER REFERENCES beneficio (id) ON DELETE SET NULL,
    origen_tramite_id  INTEGER REFERENCES tramite (id) ON DELETE SET NULL,
    tipo               TEXT NOT NULL,
    estado             TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN (
                           'pendiente', 'en_curso', 'esperando_respuesta', 'aprobado', 'rechazado')),
    motivo             TEXT,
    plazo_esperado     TEXT,
    fecha_inicio       TEXT NOT NULL DEFAULT CURRENT_DATE,
    fecha_cierre       TEXT
);

-- los pasos se copian desde paso_plantilla al crear el trámite (no se referencian)
CREATE TABLE IF NOT EXISTS paso_tramite (
    id                   INTEGER PRIMARY KEY,
    tramite_id           INTEGER NOT NULL REFERENCES tramite (id) ON DELETE CASCADE,
    orden                INTEGER NOT NULL,
    descripcion          TEXT NOT NULL,
    documento_requerido  TEXT,
    completado           INTEGER NOT NULL DEFAULT 0 CHECK (completado IN (0, 1)),
    UNIQUE (tramite_id, orden)
);

CREATE TABLE IF NOT EXISTS alerta (
    id          INTEGER PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuario (id) ON DELETE CASCADE,
    tramite_id  INTEGER REFERENCES tramite (id) ON DELETE CASCADE,
    tipo        TEXT NOT NULL,
    mensaje     TEXT NOT NULL,
    leida       INTEGER NOT NULL DEFAULT 0 CHECK (leida IN (0, 1)),
    creado_en   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ── Chat ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS conversacion (
    id           INTEGER PRIMARY KEY,
    usuario_id   INTEGER NOT NULL REFERENCES usuario (id) ON DELETE CASCADE,
    iniciada_en  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mensaje (
    id               INTEGER PRIMARY KEY,
    conversacion_id  INTEGER NOT NULL REFERENCES conversacion (id) ON DELETE CASCADE,
    rol              TEXT NOT NULL CHECK (rol IN ('usuario', 'asistente')),
    contenido        TEXT NOT NULL,
    intent           TEXT,
    creado_en        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
