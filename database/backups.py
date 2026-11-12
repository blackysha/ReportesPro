"""Copias coherentes de SQLite. Nunca sobrescribe un archivo existente."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import uuid


def crear_respaldo(origen, destino):
    origen, destino = Path(origen).resolve(), Path(destino).resolve()
    if not origen.is_file():
        raise ValueError("La base de origen no existe.")
    if origen == destino:
        raise ValueError("El destino debe ser diferente del origen.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Reserva exclusiva para evitar sobrescrituras o carreras entre respaldos.
    with destino.open("xb"):
        pass
    try:
        lectura = sqlite3.connect(origen.as_uri() + "?mode=ro", uri=True)
        try:
            copia = sqlite3.connect(destino)
            try:
                lectura.backup(copia)
                if copia.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RuntimeError("La copia no superó la comprobación de integridad.")
            finally:
                copia.close()
        finally:
            lectura.close()
    except Exception:
        destino.unlink(missing_ok=True)
        raise
    return destino


def main():
    from database.db import DB_PATH
    parser = argparse.ArgumentParser(description="Crear una copia SQLite sin cambiar el origen")
    parser.add_argument("--source", type=Path, default=DB_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    nombre = datetime.now(timezone.utc).strftime("reportespro_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8] + ".db"
    destino = args.output or Path(__file__).resolve().parents[1] / "backups" / nombre
    crear_respaldo(args.source, destino)
    print("Respaldo completado y comprobado. Mantén la copia en almacenamiento privado.")


if __name__ == "__main__":
    main()
