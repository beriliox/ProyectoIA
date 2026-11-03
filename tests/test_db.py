import sqlite3
from contextlib import closing

import pytest

from app.db import conectar, crear_tablas

TABLAS = {
    "documento_normativo", "beneficio", "regla_elegibilidad", "paso_plantilla",
    "hogar", "integrante", "usuario",
    "tramite", "paso_tramite", "alerta",
    "conversacion", "mensaje",
}


@pytest.fixture
def db(tmp_path):
    ruta = str(tmp_path / "prueba.db")
    crear_tablas(ruta)
    with closing(conectar(ruta)) as conexion:
        yield conexion


def crear_usuario_con_hogar(db) -> int:
    hogar_id = db.execute("INSERT INTO hogar (region, comuna) VALUES ('Biobío', 'Concepción')").lastrowid
    return db.execute(
        "INSERT INTO usuario (hogar_id, email, password_hash, consentimiento_datos, fecha_consentimiento) "
        "VALUES (?, 'a@b.cl', 'hash', 1, '2026-11-03')",
        (hogar_id,),
    ).lastrowid


def test_crea_todas_las_tablas_y_es_idempotente(tmp_path):
    ruta = str(tmp_path / "prueba.db")
    crear_tablas(ruta)
    crear_tablas(ruta)  # correrlo dos veces no debe fallar
    with closing(conectar(ruta)) as conexion:
        tablas = {fila["name"] for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert tablas == TABLAS


def test_rechaza_integrante_de_hogar_inexistente(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO integrante (hogar_id, parentesco, fecha_nacimiento, prevision_salud, "
            "situacion_laboral, ingreso_mensual) VALUES (999, 'titular', '1988-01-01', 'fonasa', 'cesante', 0)"
        )


def test_rechaza_tramo_fonasa_si_la_prevision_no_es_fonasa(db):
    hogar_id = db.execute("INSERT INTO hogar (region, comuna) VALUES ('Biobío', 'Concepción')").lastrowid
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO integrante (hogar_id, parentesco, fecha_nacimiento, prevision_salud, tramo_fonasa, "
            "situacion_laboral, ingreso_mensual) VALUES (?, 'titular', '1988-01-01', 'isapre', 'B', 'dependiente', 900000)",
            (hogar_id,),
        )


def test_rechaza_usuario_sin_consentimiento(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO usuario (email, password_hash, consentimiento_datos, fecha_consentimiento) "
            "VALUES ('a@b.cl', 'hash', 0, '2026-11-03')"
        )


def test_eliminar_usuario_borra_sus_tramites_y_conversaciones(db):
    usuario_id = crear_usuario_con_hogar(db)
    tramite_id = db.execute(
        "INSERT INTO tramite (usuario_id, tipo) VALUES (?, 'Actualizar RSH')", (usuario_id,)
    ).lastrowid
    db.execute("INSERT INTO paso_tramite (tramite_id, orden, descripcion) VALUES (?, 1, 'Reunir documentos')", (tramite_id,))
    conversacion_id = db.execute("INSERT INTO conversacion (usuario_id) VALUES (?)", (usuario_id,)).lastrowid
    db.execute("INSERT INTO mensaje (conversacion_id, rol, contenido) VALUES (?, 'usuario', 'hola')", (conversacion_id,))

    db.execute("DELETE FROM usuario WHERE id = ?", (usuario_id,))

    for tabla in ("tramite", "paso_tramite", "conversacion", "mensaje"):
        assert db.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0] == 0
