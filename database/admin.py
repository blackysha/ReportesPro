
"""Funciones administrativas de ReportesPro 3.0."""

import sqlite3
from database.db import conectar
from database.auditoria import registrar_evento_en_conexion
from auth.access_policy import administracion_habilitada


def preparar_roles():
    """Agrega el campo rol a los usuarios existentes."""
    with conectar() as conexion:
        columnas = {
            fila[1]
            for fila in conexion.execute(
                "PRAGMA table_info(usuarios)"
            ).fetchall()
        }

        if "rol" not in columnas:
            conexion.execute("""
                ALTER TABLE usuarios
                ADD COLUMN rol TEXT NOT NULL
                DEFAULT 'usuario'
                CHECK (rol IN ('usuario', 'admin'))
            """)


def es_administrador(usuario_id):
    """Verifica que el usuario sea administrador activo."""
    if not administracion_habilitada():
        return False
    with conectar() as conexion:
        fila = conexion.execute(
            """
            SELECT 1
            FROM usuarios
            WHERE id = ?
              AND rol = 'admin'
              AND activo = 1
            """,
            (usuario_id,),
        ).fetchone()

    return fila is not None


def listar_usuarios_admin(admin_id):
    """Lista usuarios solamente para administradores."""
    if not es_administrador(admin_id):
        raise PermissionError(
            "No tienes permisos de administrador."
        )

    with conectar() as conexion:
        conexion.row_factory = sqlite3.Row

        filas = conexion.execute("""
            SELECT id, nombre, correo, activo, rol,
                   fecha_creacion
            FROM usuarios
            ORDER BY id
        """).fetchall()

    return [dict(fila) for fila in filas]


def cambiar_estado_usuario(admin_id, usuario_id, activo):
    """Activa o desactiva una cuenta con autorización."""
    if not administracion_habilitada():
        raise PermissionError("La administración solo está disponible en la consola local.")
    if not isinstance(activo, bool):
        raise ValueError(
            "El estado debe ser True o False."
        )

    with conectar() as conexion:
        conexion.execute("BEGIN IMMEDIATE")

        administrador = conexion.execute(
            """
            SELECT 1 FROM usuarios
            WHERE id = ? AND rol = 'admin' AND activo = 1
            """,
            (admin_id,),
        ).fetchone()

        if administrador is None:
            raise PermissionError(
                "No tienes permisos de administrador."
            )

        if admin_id == usuario_id:
            raise ValueError(
                "No puedes cambiar tu propio estado "
                "desde el panel administrativo."
            )

        destino = conexion.execute(
            "SELECT id, activo FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()

        if destino is None:
            raise ValueError("El usuario no existe.")

        if destino[1] == int(activo):
            return True

        conexion.execute(
            """
            UPDATE usuarios
            SET activo = ?, version_sesion = version_sesion + 1
            WHERE id = ?
            """,
            (int(activo), usuario_id),
        )
        registrar_evento_en_conexion(
            conexion, usuario_id,
            "CUENTA_ACTIVADA" if activo else "CUENTA_DESACTIVADA",
            f"Cambio administrativo por usuario {admin_id}",
        )

    return True
