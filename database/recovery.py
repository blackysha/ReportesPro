
"""Recuperación segura de contraseñas de ReportesPro 3.0."""

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from auth.security import crear_hash_password
from database.db import conectar


DURACION_USUARIO_MINUTOS = 15
MAX_SOLICITUDES_POR_HORA = 3


def fecha_actual():
    return datetime.now(timezone.utc)


def preparar_recuperacion():
    """Crea la tabla sin modificar los datos existentes."""

    with conectar() as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS recuperaciones_password (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                fecha_creacion TEXT NOT NULL,
                fecha_expiracion TEXT NOT NULL,
                fecha_utilizacion TEXT,
                FOREIGN KEY (usuario_id)
                    REFERENCES usuarios(id)
            )
            """
        )

        conexion.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_recuperacion_usuario_fecha
            ON recuperaciones_password (
                usuario_id,
                fecha_creacion
            )
            """
        )


def hash_token(token):
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def solicitar_recuperacion(correo):
    """
    Genera un token únicamente para usuarios normales activos.

    Devuelve (token, correo) o None.

    La interfaz pública siempre debe mostrar una respuesta
    genérica, independientemente de este resultado.

    Los administradores requieren un flujo separado con TOTP.
    """

    correo = correo.strip().lower()

    if not correo:
        return None

    ahora = fecha_actual()

    with conectar() as conexion:
        conexion.execute("BEGIN IMMEDIATE")

        usuario = conexion.execute(
            """
            SELECT id, correo, rol
            FROM usuarios
            WHERE lower(correo) = ?
              AND activo = 1
            """,
            (correo,),
        ).fetchone()

        if usuario is None:
            return None

        usuario_id, correo_real, rol = usuario

        # No permitir recuperación de administradores
        # sin el segundo factor.
        if rol != "usuario":
            return None

        desde = (
            ahora - timedelta(hours=1)
        ).isoformat()

        solicitudes = conexion.execute(
            """
            SELECT COUNT(*)
            FROM recuperaciones_password
            WHERE usuario_id = ?
              AND fecha_creacion >= ?
            """,
            (usuario_id, desde),
        ).fetchone()[0]

        if solicitudes >= MAX_SOLICITUDES_POR_HORA:
            return None

        token = secrets.token_urlsafe(32)

        expiracion = (
            ahora + timedelta(
                minutes=DURACION_USUARIO_MINUTOS
            )
        ).isoformat()

        # Invalidar enlaces anteriores.
        conexion.execute(
            """
            UPDATE recuperaciones_password
            SET fecha_utilizacion = ?
            WHERE usuario_id = ?
              AND fecha_utilizacion IS NULL
            """,
            (ahora.isoformat(), usuario_id),
        )

        conexion.execute(
            """
            INSERT INTO recuperaciones_password (
                usuario_id,
                token_hash,
                fecha_creacion,
                fecha_expiracion
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                usuario_id,
                hash_token(token),
                ahora.isoformat(),
                expiracion,
            ),
        )


        # Registrar la solicitud de recuperación.
        # No almacenar el token ni el correo en auditoría.
        conexion.execute(
            """
            INSERT INTO auditoria_seguridad (
                usuario_id,
                evento,
                detalle,
                fecha
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                usuario_id,
                "RECUPERACION_SOLICITADA",
                "Token de recuperación generado",
                ahora.isoformat(),
            ),
        )


    return token, correo_real


def restablecer_password(token, nueva_password):
    """
    Valida y consume un token de recuperación.

    Solo admite cuentas normales activas.
    La operación se realiza en una transacción.
    """

    if not isinstance(token, str) or not 20 <= len(token) <= 128:
        return False

    # Validar y generar el hash antes de modificar SQLite.
    nuevo_hash = crear_hash_password(nueva_password)
    ahora = fecha_actual().isoformat()

    with conectar() as conexion:
        conexion.execute("BEGIN IMMEDIATE")

        recuperacion = conexion.execute(
            """
            SELECT r.id, r.usuario_id
            FROM recuperaciones_password r
            JOIN usuarios u ON u.id = r.usuario_id
            WHERE r.token_hash = ?
              AND r.fecha_utilizacion IS NULL
              AND r.fecha_expiracion > ?
              AND u.activo = 1
              AND u.rol = 'usuario'
            """,
            (hash_token(token), ahora),
        ).fetchone()

        if recuperacion is None:
            return False

        recuperacion_id, usuario_id = recuperacion

        cursor = conexion.execute(
            """
            UPDATE usuarios
            SET password_hash = ?,
                version_sesion = version_sesion + 1
              WHERE id = ?
                AND activo = 1
                AND rol = 'usuario'
            """,
            (nuevo_hash, usuario_id),
        )

        if cursor.rowcount != 1:
            return False


        # Consumir el token e invalidar otros pendientes.
        conexion.execute(
            """
            UPDATE recuperaciones_password
            SET fecha_utilizacion = ?
            WHERE usuario_id = ?
              AND fecha_utilizacion IS NULL
            """,
            (ahora, usuario_id),
        )

        # Registrar el restablecimiento en auditoría.
        # Se ejecuta dentro de la misma transacción SQLite.
        conexion.execute(
            """
            INSERT INTO auditoria_seguridad (
                usuario_id,
                evento,
                detalle,
                fecha
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                usuario_id,
                "PASSWORD_RESTABLECIDA",
                "Contraseña restablecida mediante enlace de recuperación",
                ahora,
            ),
        )

        return True
