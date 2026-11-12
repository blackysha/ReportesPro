
"""Prueba aislada de autenticacion de ReportesPro 3.0."""

import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from auth.security import crear_hash_password, verificar_password
from database import login_security


def ejecutar_prueba():
    correo = "prueba-autenticacion@example.com"
    clave_correcta = "ClaveTemporalSegura2026!"
    clave_incorrecta = "ClaveIncorrecta123!"

    @contextmanager
    def conectar_prueba():
        conexion = sqlite3.connect(ruta, timeout=10)
        try:
            with conexion:
                yield conexion
        finally:
            conexion.close()

    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "prueba_login.db"

        with conectar_prueba() as conexion:
            conexion.execute("""
                CREATE TABLE usuarios (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    correo TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    activo INTEGER NOT NULL DEFAULT 1,
                    version_sesion INTEGER NOT NULL DEFAULT 0,
                    rol TEXT NOT NULL DEFAULT 'usuario'
                )
            """)

            conexion.execute(
                """
                INSERT INTO usuarios
                (nombre, correo, password_hash, activo)
                VALUES (?, ?, ?, 1)
                """,
                (
                    "Usuario de Prueba",
                    correo,
                    crear_hash_password(clave_correcta),
                ),
            )

        with conectar_prueba() as conexion:
            conexion.execute("""CREATE TABLE auditoria_seguridad (
                id INTEGER PRIMARY KEY, usuario_id INTEGER, evento TEXT,
                detalle TEXT, fecha TEXT
            )""")

        with patch.object(
            login_security,
            "conectar",
            conectar_prueba,
        ):
            login_security.preparar_seguridad_login()

            for numero in range(1, 4):
                resultado = login_security.autenticar_con_proteccion(
                    correo,
                    clave_incorrecta,
                    verificar_password,
                )
                print(
                    f"Intento incorrecto {numero}:",
                    resultado is None,
                )

            assert resultado is None, "Credenciales incorrectas aceptadas"
            identificador = login_security._identificador(correo)

            with conectar_prueba() as conexion:
                fila = conexion.execute(
                    """
                    SELECT intentos
                    FROM intentos_login
                    WHERE identificador = ?
                    """,
                    (identificador,),
                ).fetchone()

            print(
                "Intentos acumulados:",
                fila[0] if fila else None,
            )

            usuario = login_security.autenticar_con_proteccion(
                correo,
                clave_correcta,
                verificar_password,
            )

            print(
                "Autenticacion correcta:",
                usuario is not None,
            )

            with conectar_prueba() as conexion:
                fila = conexion.execute(
                    """
                    SELECT intentos
                    FROM intentos_login
                    WHERE identificador = ?
                    """,
                    (identificador,),
                ).fetchone()

            print("Contador eliminado:", fila is None)
            assert fila is None, "Contador no eliminado"

            for _ in range(5):
                login_security.autenticar_con_proteccion(
                    correo,
                    clave_incorrecta,
                    verificar_password,
                )

            print(
                "Bloqueo activado:",
                login_security.consultar_bloqueo(correo) > 0,
            )

            assert login_security.consultar_bloqueo(correo) > 0
            usuario_bloqueado = (
                login_security.autenticar_con_proteccion(
                    correo,
                    clave_correcta,
                    verificar_password,
                )
            )

            print(
                "Clave correcta rechazada durante bloqueo:",
                usuario_bloqueado is None,
            )

            assert usuario_bloqueado is None, "Bloqueo omitido"

    print("Base de datos temporal eliminada correctamente.")
    print("Prueba finalizada.")


if __name__ == "__main__":
    ejecutar_prueba()
