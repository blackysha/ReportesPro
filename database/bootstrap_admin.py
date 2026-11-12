
"""Inicialización segura del primer administrador de ReportesPro."""

import getpass
import sqlite3
import sys

from auth.security import verificar_password
from database.db import conectar
from database.usuarios import (
    crear_tabla_usuarios,
    preparar_estado_cuentas,
)
from database.admin import preparar_roles


def crear_primer_administrador():
    """
    Asigna el rol admin a una cuenta existente.

    Solo funciona cuando todavía no hay administradores.
    Debe ejecutarse manualmente desde la terminal local.
    """

    crear_tabla_usuarios()
    preparar_estado_cuentas()
    preparar_roles()

    print("\n=== REPORTESPRO: PRIMER ADMINISTRADOR ===")
    print("Esta operación solo debe ejecutarse en un entorno confiable.")
    print("No introduzcas contraseñas en argumentos de terminal.\n")

    try:
        usuario_id = int(input("ID del usuario administrador: ").strip())
    except ValueError:
        print("Error: introduce un ID numérico.")
        return False

    if usuario_id <= 0:
        print("Error: el ID debe ser positivo.")
        return False

    # Obtener los datos de la cuenta sin exponer su contraseña.
    with conectar() as conexion:
        conexion.row_factory = sqlite3.Row

        usuario = conexion.execute(
            """
            SELECT id, nombre, correo, activo, rol
            FROM usuarios
            WHERE id = ?
            """,
            (usuario_id,),
        ).fetchone()

        administradores = conexion.execute(
            """
            SELECT COUNT(*)
            FROM usuarios
            WHERE rol = 'admin'
            """
        ).fetchone()[0]

    if administradores > 0:
        print(
            "Operación bloqueada: ya existe un administrador. "
            "No es posible repetir la inicialización."
        )
        return False

    if usuario is None:
        print("Error: el usuario indicado no existe.")
        return False

    if usuario["activo"] != 1:
        print("Error: la cuenta está desactivada.")
        return False

    print("\nCuenta seleccionada:")
    print(f"ID: {usuario['id']}")
    print(f"Nombre: {usuario['nombre']}")
    print(f"Correo: {usuario['correo']}")

    confirmacion = input(
        "\nEscribe CONFIRMAR para continuar: "
    ).strip()

    if confirmacion != "CONFIRMAR":
        print("Operación cancelada.")
        return False

    password = getpass.getpass(
        "Contraseña de esta cuenta (no se mostrará): "
    )

    # Se comprueba el estado nuevamente dentro de la transacción
    # para evitar cambios simultáneos durante la asignación.
    try:
        with conectar() as conexion:
            conexion.row_factory = sqlite3.Row
            conexion.execute("BEGIN IMMEDIATE")

            existe_admin = conexion.execute(
                """
                SELECT 1
                FROM usuarios
                WHERE rol = 'admin'
                LIMIT 1
                """
            ).fetchone()

            if existe_admin is not None:
                print("Ya existe un administrador. Operación cancelada.")
                return False

            cuenta = conexion.execute(
                """
                SELECT id, activo, password_hash
                FROM usuarios
                WHERE id = ?
                """,
                (usuario_id,),
            ).fetchone()

            if cuenta is None or cuenta["activo"] != 1:
                print("La cuenta no está activa o no existe.")
                return False

            if not verificar_password(
                password, cuenta["password_hash"]
            ):
                print("Contraseña incorrecta. Operación cancelada.")
                return False

            cursor = conexion.execute(
                """
                UPDATE usuarios
                SET rol = 'admin'
                WHERE id = ? AND activo = 1
                """,
                (usuario_id,),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "No se pudo actualizar el rol."
                )

        print("\nAdministrador creado correctamente.")
        print(f"Usuario ID {usuario_id}: rol admin.")
        return True

    except sqlite3.Error as exc:
        print(f"Error de base de datos: {exc}")
        return False


if __name__ == "__main__":
    if not sys.stdin.isatty():
        print(
            "Error: ejecuta este programa desde "
            "una terminal interactiva."
        )
        sys.exit(1)

    resultado = crear_primer_administrador()
    sys.exit(0 if resultado else 1)
