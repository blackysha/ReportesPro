
"""Gestión de usuarios de ReportesPro 3.0."""

import sqlite3
import re

from database.db import conectar
from auth.security import crear_hash_password, verificar_password
from database.login_security import autenticar_con_proteccion
from database.auditoria import registrar_evento_en_conexion
from auth.access_policy import administracion_habilitada


def crear_tabla_usuarios():
    """Crea la tabla de usuarios si no existe."""

    with conectar() as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                correo TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def registrar_usuario(nombre, correo, password):
    """Registra una cuenta nueva."""

    nombre = nombre.strip()
    correo = correo.strip().lower()

    if not nombre or len(nombre) > 120:
        raise ValueError("El nombre es obligatorio.")

    if len(correo) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
        raise ValueError("Introduce un correo válido.")

    password_hash = crear_hash_password(password)

    try:
        with conectar() as conexion:
            cursor = conexion.execute(
                """
                INSERT INTO usuarios (
                    nombre,
                    correo,
                    password_hash
                )
                VALUES (?, ?, ?)
                """,
                (nombre, correo, password_hash),
            )

            return cursor.lastrowid

    except sqlite3.IntegrityError:
        raise ValueError(
            "Ya existe una cuenta con ese correo."
        ) from None


def autenticar_usuario(correo, password):
    """
    Autentica usuarios aplicando protección
    contra intentos de fuerza bruta.
    """

    return autenticar_con_proteccion(
        correo,
        password,
        verificar_password,
    )


def preparar_estado_cuentas():
    """Agrega la columna activo sin eliminar usuarios existentes."""

    with conectar() as conexion:
        columnas = {
            fila[1]
            for fila in conexion.execute(
                "PRAGMA table_info(usuarios)"
            ).fetchall()
        }

        if "activo" not in columnas:
            conexion.execute(
                """
                ALTER TABLE usuarios
                ADD COLUMN activo INTEGER NOT NULL DEFAULT 1
                CHECK (activo IN (0, 1))
                """
            )


def cuenta_activa(usuario_id):
    """Comprueba que la cuenta existe y está activa."""

    with conectar() as conexion:
        fila = conexion.execute(
            """
            SELECT activo
            FROM usuarios
            WHERE id = ?
            """,
            (usuario_id,),
        ).fetchone()

    return fila is not None and fila[0] == 1


def desactivar_mi_cuenta(usuario_id, password):
    """
    Desactiva la cuenta tras comprobar la contraseña.
    No elimina empresas ni reportes.
    """

    with conectar() as conexion:
        conexion.execute("BEGIN IMMEDIATE")
        conexion.row_factory = sqlite3.Row

        usuario = conexion.execute(
            """
            SELECT id, password_hash, activo, rol
            FROM usuarios
            WHERE id = ?
            """,
            (usuario_id,),
        ).fetchone()

        if usuario is None or usuario["activo"] != 1:
            raise ValueError("La cuenta no está activa.")

        if not verificar_password(
            password,
            usuario["password_hash"],
        ):
            raise ValueError("Contraseña incorrecta.")

        if usuario["rol"] == "admin":
            administradores = conexion.execute(
                "SELECT COUNT(*) FROM usuarios WHERE rol = 'admin' AND activo = 1"
            ).fetchone()[0]
            if administradores <= 1:
                raise ValueError("El último administrador activo no puede desactivar su cuenta.")

        conexion.execute(
            """
            UPDATE usuarios
            SET activo = 0, version_sesion = version_sesion + 1
            WHERE id = ? AND activo = 1
            """,
            (usuario_id,),
        )
        registrar_evento_en_conexion(conexion, usuario_id, "CUENTA_DESACTIVADA", "Desactivación propia")

    return True


def preparar_version_sesiones():
    """
    Agrega un contador de versión para invalidar sesiones.
    Conserva los usuarios y sus datos actuales.
    """

    with conectar() as conexion:
        columnas = {
            fila[1]
            for fila in conexion.execute(
                "PRAGMA table_info(usuarios)"
            ).fetchall()
        }

        if "version_sesion" not in columnas:
            conexion.execute(
                """
                ALTER TABLE usuarios
                ADD COLUMN version_sesion
                INTEGER NOT NULL DEFAULT 0
                """
            )


def obtener_version_sesion(usuario_id):
    """Devuelve la versión de sesión de una cuenta activa."""

    with conectar() as conexion:
        fila = conexion.execute(
            """
            SELECT version_sesion
            FROM usuarios
            WHERE id = ?
              AND activo = 1
              AND (? = 1 OR rol != 'admin')
            """,
            (usuario_id, int(administracion_habilitada())),
        ).fetchone()

    if fila is None:
        return None

    return fila[0]
