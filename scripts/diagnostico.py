"""Comprobación local de solo lectura, sin mostrar datos de cuentas."""

import argparse
from importlib.metadata import PackageNotFoundError, version
import sqlite3

from database.db import DB_PATH
from database.schema import REQUERIDAS


def main():
    parser = argparse.ArgumentParser(description="Comprobar dependencias y esquema sin modificar datos")
    parser.add_argument("--security-config", action="store_true", help="Comprobar presencia y longitud de la clave sin mostrarla")
    args = parser.parse_args()
    correcto = True
    for package in ("streamlit", "pandas", "reportlab", "openpyxl", "xlrd", "argon2-cffi"):
        try:
            print(f"{package}: {version(package)}")
        except PackageNotFoundError:
            print(f"{package}: NO INSTALADO")
            correcto = False
    if not DB_PATH.is_file():
        print("Base de datos: no existe; no se creó ninguna")
        correcto = False
    else:
        c = sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True)
        try:
            for table, required in REQUERIDAS.items():
                found = {row[1] for row in c.execute(f"PRAGMA table_info({table})")}
                if not required <= found:
                    print(f"Esquema incompleto: {table}")
                    correcto = False
            integrity = c.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            foreign_keys = not c.execute("PRAGMA foreign_key_check").fetchall()
            print(f"Integridad: {'OK' if integrity else 'REVISAR'}")
            print(f"Claves foráneas: {'OK' if foreign_keys else 'REVISAR'}")
            correcto = correcto and integrity and foreign_keys
        finally:
            c.close()
    if args.security_config:
        from database.login_security import _clave_seguridad
        try:
            _clave_seguridad()
            print("Configuración LOGIN_SECURITY_KEY: válida (valor oculto)")
        except Exception:
            print("Configuración LOGIN_SECURITY_KEY: requiere revisión (valor oculto)")
            correcto = False
    print("Diagnóstico: " + ("OK" if correcto else "REQUIERE REVISIÓN"))
    return 0 if correcto else 1


if __name__ == "__main__":
    raise SystemExit(main())
