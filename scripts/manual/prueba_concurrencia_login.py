
"""Prueba aislada de concurrencia para ReportesPro 3.0."""

import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from database import login_security


def ejecutar_prueba():
    correo = "concurrencia-prueba@example.com"
    cantidad_intentos = 10

    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "concurrencia.db"

        @contextmanager
        def conectar_prueba():
            conexion = sqlite3.connect(ruta, timeout=15)
            try:
                with conexion:
                    yield conexion
            finally:
                conexion.close()

        with conectar_prueba() as conexion:
            conexion.execute(
                """
                CREATE TABLE usuarios (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    correo TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    activo INTEGER NOT NULL DEFAULT 1,
                    version_sesion INTEGER NOT NULL DEFAULT 0,
                    rol TEXT NOT NULL DEFAULT 'usuario'
                )
                """
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

            barrera = Barrier(cantidad_intentos)

            def intentar_login(numero):
                barrera.wait(timeout=15)

                resultado = login_security.autenticar_con_proteccion(
                    correo,
                    "ClaveIncorrecta123!",
                    lambda password, hash_guardado: False,
                )

                return numero, resultado is None

            with ThreadPoolExecutor(
                max_workers=cantidad_intentos
            ) as ejecutor:
                resultados = list(
                    ejecutor.map(
                        intentar_login,
                        range(1, cantidad_intentos + 1),
                    )
                )

            identificador = login_security._identificador(correo)

            with conectar_prueba() as conexion:
                fila = conexion.execute(
                    """
                    SELECT intentos, bloqueado_hasta
                    FROM intentos_login
                    WHERE identificador = ?
                    """,
                    (identificador,),
                ).fetchone()

            rechazados = sum(
                1 for _, rechazado in resultados if rechazado
            )

            print("Solicitudes simultaneas:", cantidad_intentos)
            print("Solicitudes rechazadas:", rechazados)
            print("Intentos registrados:", fila[0] if fila else None)
            print(
                "Bloqueo activado:",
                login_security.consultar_bloqueo(correo) > 0,
            )

            correcto = (
                rechazados == cantidad_intentos
                and fila is not None
                and fila[0] == login_security.MAX_INTENTOS
                and login_security.consultar_bloqueo(correo) > 0
            )

            print("PRUEBA SUPERADA:", correcto)
            assert correcto, "Fallo de concurrencia"

    print("Base de datos temporal eliminada.")


if __name__ == "__main__":
    ejecutar_prueba()
