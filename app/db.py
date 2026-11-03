"""Capa de datos: conexión a SQLite y creación de tablas. En Docker solo cambia RUTA_DB."""
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RUTA_DB = os.getenv("RUTA_DB", "app/app.db")
ESQUEMA = Path(__file__).with_name("schema.sql")


def conectar(ruta: str = RUTA_DB) -> sqlite3.Connection:
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row  # filas accesibles por nombre de columna
    conexion.execute("PRAGMA foreign_keys = ON")  # SQLite no valida las FK si no se le pide
    return conexion


def crear_tablas(ruta: str = RUTA_DB) -> None:
    """Idempotente: el esquema usa CREATE TABLE IF NOT EXISTS."""
    with closing(conectar(ruta)) as conexion:
        conexion.executescript(ESQUEMA.read_text(encoding="utf-8"))


if __name__ == "__main__":
    crear_tablas()
    print(f"Base de datos lista en {RUTA_DB}")
